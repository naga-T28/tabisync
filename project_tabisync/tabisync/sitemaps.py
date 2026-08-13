from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

# インデックス対象の公開ページのみを列挙する。対象・非対象は
# docs/task/task-004-seo-improvements.md のインデックス方針表と一致させること。
# お問い合わせは本文が薄いフォーム中心のページのため、内容を拡充するまで
# サイトマップには含めない（meta robotsの索引可否とは独立）。
# しおり作成（create）はTask 005で作成手順・機能説明の本文を追加したため含める。
SITEMAP_URL_NAMES = [
    "tabisync:home",
    "tabisync:qa",
    "tabisync:updates",
    "tabisync:profile",
    "tabisync:user_agreement",
    "tabisync:concierge_terms",
    "tabisync:privacy_policy",
    "tabisync:create",
    "tabisync:guide_sample",
    "tabisync:guide_no_signup",
    "tabisync:guide_collaboration",
    "tabisync:guide_all_in_one",
    "tabisync:guide_ai_concierge",
]


class StaticViewSitemap(Sitemap):
    # 全ページに同じchangefreq/priorityを機械的に付けると検索順位向上の裏付けが
    # ないまま数値だけが残るため、既定値は付けない（Sitemap側の既定はNoneでXML出力自体を省略する）。

    def items(self):
        return SITEMAP_URL_NAMES

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        if item != "tabisync:updates":
            return None
        # 更新情報ページの最終更新は、根拠のない現在時刻を毎回返す代わりに、
        # 実際にテンプレートを編集した時点を反映するファイルの更新日時を使う。
        template_path = Path(settings.BASE_DIR) / "templates" / "docs" / "update.html"
        try:
            mtime = template_path.stat().st_mtime
        except OSError:
            return None
        return datetime.fromtimestamp(mtime, tz=dt_timezone.utc)

    def get_domain(self, site=None):
        return urlsplit(settings.PUBLIC_BASE_URL).netloc

    def get_protocol(self, protocol=None):
        return urlsplit(settings.PUBLIC_BASE_URL).scheme
