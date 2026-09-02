import hashlib
import html.parser
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request

from django.core.cache import cache

LINK_PREVIEW_TIMEOUT_SECONDS = 5
LINK_PREVIEW_MAX_BYTES = 512 * 1024
LINK_PREVIEW_MAX_REDIRECTS = 3
LINK_PREVIEW_CACHE_SECONDS = 60 * 60 * 24
LINK_PREVIEW_USER_AGENT = "TabiSyncLinkPreviewBot/1.0"
MAX_LINK_PREVIEW_URLS_PER_REQUEST = 6

_OG_TEXT_KEYS = ("og:title", "og:site_name", "og:description", "description")


def _is_public_hostname(hostname):
    """SSRF対策: ホスト名が解決する全アドレスがパブリックユニキャストであることを確認する。"""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        raw_ip = info[4][0].split("%")[0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def _extract_charset(content_type):
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip().strip('"')
    return None


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _OGPParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.og = {}
        self.title = None
        self._in_title = False
        self._head_closed = False

    def handle_starttag(self, tag, attrs):
        if self._head_closed:
            return
        attrs_dict = {key.lower(): value for key, value in attrs if key}
        if tag == "meta":
            prop = (attrs_dict.get("property") or attrs_dict.get("name") or "").strip().lower()
            content = attrs_dict.get("content")
            if prop == "og:image" and content and "og:image" not in self.og:
                self.og["og:image"] = content.strip()
            elif prop in _OG_TEXT_KEYS and content and prop not in self.og:
                self.og[prop] = content.strip()
        elif tag == "title" and self.title is None:
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self._head_closed = True

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip()


def _fetch_html(url):
    current_url = url
    opener = urllib.request.build_opener(_NoRedirectHandler)

    for _ in range(LINK_PREVIEW_MAX_REDIRECTS + 1):
        parsed = urllib.parse.urlparse(current_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        if not _is_public_hostname(parsed.hostname):
            return None

        request = urllib.request.Request(
            current_url,
            headers={"User-Agent": LINK_PREVIEW_USER_AGENT, "Accept": "text/html"},
        )
        try:
            with opener.open(request, timeout=LINK_PREVIEW_TIMEOUT_SECONDS) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    return None
                raw = response.read(LINK_PREVIEW_MAX_BYTES)
                charset = _extract_charset(content_type) or "utf-8"
                try:
                    return raw.decode(charset, errors="ignore")
                except LookupError:
                    return raw.decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location")
                if not location:
                    return None
                current_url = urllib.parse.urljoin(current_url, location)
                continue
            return None
        except (urllib.error.URLError, socket.timeout, ValueError, ConnectionError):
            return None

    return None


def _build_preview(url):
    parsed = urllib.parse.urlparse(url)
    preview = {
        "url": url,
        "domain": parsed.hostname or "",
        "title": None,
        "image": None,
        "site_name": None,
    }

    html_text = _fetch_html(url)
    if not html_text:
        return preview

    parser = _OGPParser()
    try:
        parser.feed(html_text)
    except Exception:
        return preview

    title = parser.og.get("og:title") or parser.title
    if title:
        preview["title"] = title[:200]

    site_name = parser.og.get("og:site_name")
    if site_name:
        preview["site_name"] = site_name[:100]

    image = parser.og.get("og:image")
    if image:
        absolute_image = urllib.parse.urljoin(url, image)
        if urllib.parse.urlparse(absolute_image).scheme in ("http", "https"):
            preview["image"] = absolute_image

    return preview


def get_link_preview(url):
    """URLのOGPプレビュー(title/image/site_name)をキャッシュ付きで取得する。
    取得に失敗しても例外は投げず、domain/urlのみのdictを返す(呼び出し側はフォールバック表示に使う)。"""
    cache_key = "concierge_link_preview:" + hashlib.sha256(url.encode("utf-8")).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    preview = _build_preview(url)
    cache.set(cache_key, preview, LINK_PREVIEW_CACHE_SECONDS)
    return preview
