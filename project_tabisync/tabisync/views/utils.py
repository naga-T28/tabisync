import ipaddress
import json
import logging
import os
import re
import urllib.parse
import urllib.request

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.html import strip_tags


logger = logging.getLogger(__name__)

CONCIERGE_USER_MESSAGE_MAX_LENGTH = 60
MAX_ITINERARY_DAYS = 30
MAX_SCHEDULES_PER_DAY = 15
MAX_MEMOS_PER_ITINERARY = 15
MAX_MEMO_WORDS = 1000
MAX_CHECKLISTS_PER_ITINERARY = 10
MAX_CHECKLIST_ITEMS_PER_LIST = 30
MAX_COVER_IMAGE_SIZE = settings.MAX_COVER_IMAGE_UPLOAD_BYTES
ALLOWED_COVER_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MEMO_WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[぀-ヿ㐀-鿿]")
TURNSTILE_TIMEOUT_SECONDS = float(os.environ.get("TURNSTILE_TIMEOUT_SECONDS", "5"))
MAX_JSON_BODY_BYTES = int(os.environ.get("MAX_JSON_BODY_BYTES", str(256 * 1024)))


# =========================
# 基本ユーティリティ
# =========================
def offline_view(request):
    return render(request, "offline.html")



# クローラ対策
def robots_txt_view(request):
    lines = [
        "User-agent: *",
        "Disallow: /content/",
        "Disallow: /reset-link/",
        "Disallow: /reset/",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")



def verify_turnstile(request):
    secret_key = os.environ.get('CLOUDFLARE_TURNSTILE_SECRET_KEY')
    if not secret_key:
        logger.error("CLOUDFLARE_TURNSTILE_SECRET_KEY is not configured; rejecting Turnstile verification.")
        return False

    token = request.POST.get('cf-turnstile-response')
    if not token:
        return False

    remoteip = get_client_ip(request)

    data = urllib.parse.urlencode({
        'secret': secret_key,
        'response': token,
        'remoteip': remoteip,
    }).encode()

    req = urllib.request.Request(
        url='https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data=data,
        method='POST'
    )
    req.add_header("Content-type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=TURNSTILE_TIMEOUT_SECONDS) as resp:
            response_data = json.loads(resp.read().decode())
            return response_data.get('success', False)
    except Exception:
        logger.warning("Turnstile verification request failed.", exc_info=True)
        return False



UNKNOWN_CLIENT_IP = "unknown"


def _is_trusted_proxy_addr(remote_addr):
    # REMOTE_ADDR（直前のホップ）が信頼済みプロキシのCIDRに含まれる場合のみTrue。
    # settings.TRUSTED_PROXY_CIDRSが未設定なら常にFalse（転送ヘッダーは信頼しない）。
    if not remote_addr:
        return False

    try:
        addr = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False

    for cidr in getattr(settings, "TRUSTED_PROXY_CIDRS", None) or []:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            logger.warning("Ignoring invalid TRUSTED_PROXY_CIDRS entry: %r", cidr)
            continue
        if addr in network:
            return True

    return False


def get_client_ip(request):
    remote_addr = (request.META.get("REMOTE_ADDR") or "").strip()

    # 直前のホップが信頼済みプロキシの場合のみ、転送ヘッダーの値を採用する。
    # 未信頼の送信元からの偽装ヘッダーは無視する。
    if _is_trusted_proxy_addr(remote_addr):
        cf_connecting_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_connecting_ip:
            candidate = cf_connecting_ip.strip()
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                logger.warning("Ignoring invalid CF-Connecting-IP header: %r", cf_connecting_ip)

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            for part in x_forwarded_for.split(","):
                candidate = part.strip()
                if not candidate:
                    continue
                try:
                    ipaddress.ip_address(candidate)
                    return candidate
                except ValueError:
                    continue

    try:
        ipaddress.ip_address(remote_addr)
        return remote_addr
    except ValueError:
        # REMOTE_ADDRが取得できない/不正な場合、空文字を共有キーにして
        # 利用者全員が同一のレート制限バケットに混在しないよう明示的な代替キーを返す。
        logger.warning("Unable to determine a valid client IP; REMOTE_ADDR=%r", remote_addr)
        return UNKNOWN_CLIENT_IP



def ratelimit_client_ip(_group, request):
    return get_client_ip(request)



def build_public_service_error_message(exc, default_message):
    if settings.DEBUG:
        return str(exc)

    detail = str(exc).lower()
    if "timeout" in detail:
        return "現在アクセスが集中しています。しばらくしてから再度お試しください。"
    return default_message



def get_inclusive_day_count(start_date, end_date):
    return (end_date - start_date).days + 1



def count_memo_words(content):
    text = strip_tags(str(content or ""))
    return len(MEMO_WORD_PATTERN.findall(text))



def validate_memo_notes_limits(notes):
    if len(notes) > MAX_MEMOS_PER_ITINERARY:
        return f"メモは最大{MAX_MEMOS_PER_ITINERARY}件まで保存できます。"

    for index, note in enumerate(notes, start=1):
        if count_memo_words(note.get("content", "")) > MAX_MEMO_WORDS:
            return f"メモ{index}は{MAX_MEMO_WORDS}語まで保存できます。"

    return None



def validate_checklist_limits(lists):
    if len(lists) > MAX_CHECKLISTS_PER_ITINERARY:
        return f"リストは最大{MAX_CHECKLISTS_PER_ITINERARY}リストまで保存できます。"

    for index, item_list in enumerate(lists, start=1):
        items = item_list.get("items", [])
        if len(items) > MAX_CHECKLIST_ITEMS_PER_LIST:
            title = item_list.get("title") or f"リスト{index}"
            return f"{title}は{MAX_CHECKLIST_ITEMS_PER_LIST}個まで保存できます。"

    return None



def parse_json_object_body(request, max_bytes=None):
    """JSON APIエンドポイント共通のリクエストボディ検証。

    Content-Type必須チェック→サイズ上限→UTF-8デコード→JSONデコード→
    トップレベルがオブジェクト(dict)かどうかを検証する。
    成功時は (dict, None) を、失敗時は (None, 400のJsonResponse) を返す。
    """
    limit = max_bytes if max_bytes is not None else MAX_JSON_BODY_BYTES

    content_type = request.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return None, JsonResponse({
            "status": "error",
            "message": "Content-Typeはapplication/jsonである必要があります。",
        }, status=400)

    body = request.body
    if len(body) > limit:
        return None, JsonResponse({"status": "error", "message": "リクエストボディが大きすぎます。"}, status=400)

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return None, JsonResponse({"status": "error", "message": "不正なUTF-8です。"}, status=400)

    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None, JsonResponse({"status": "error", "message": "不正なJSONです。"}, status=400)

    if not isinstance(data, dict):
        return None, JsonResponse({
            "status": "error",
            "message": "JSONのトップレベルはオブジェクトである必要があります。",
        }, status=400)

    return data, None

