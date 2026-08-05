import ipaddress
import logging
import os
import re
import urllib.parse
import urllib.request

from django.conf import settings
from django.http import HttpResponse
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
    token = request.POST.get('cf-turnstile-response')
    remoteip = request.META.get('REMOTE_ADDR')

    if not token:
        return False

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
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode())
            return response_data.get('success', False)
    except Exception as e:
        print("Turnstile verify error:", e)
        return False



def get_client_ip(request):
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

    remote_addr = (request.META.get("REMOTE_ADDR") or "").strip()
    try:
        ipaddress.ip_address(remote_addr)
        return remote_addr
    except ValueError:
        return ""



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

