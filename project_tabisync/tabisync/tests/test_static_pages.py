import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.staticfiles.views import serve as serve_static
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from PIL import Image

from ..content_data import (
    FAQ_SECTIONS,
    GUIDE_AI_CONCIERGE_FAQ,
    GUIDE_ALL_IN_ONE_FAQ,
    GUIDE_COLLABORATION_FAQ,
    GUIDE_NO_SIGNUP_FAQ,
    GUIDE_SAMPLE_FAQ,
)
from ..models import Itinerary
from ..sitemaps import SITEMAP_TEMPLATE_PATHS, SITEMAP_URL_NAMES, StaticViewSitemap


PUBLIC_URL_NAMES = [
    "tabisync:home",
    "tabisync:qa",
    "tabisync:profile",
    "tabisync:user_agreement",
    "tabisync:concierge_terms",
    "tabisync:privacy_policy",
    "tabisync:updates",
    "tabisync:create",
    "tabisync:guide_sample",
    "tabisync:guide_no_signup",
    "tabisync:guide_collaboration",
    "tabisync:guide_all_in_one",
    "tabisync:guide_ai_concierge",
]

# パンくず・FAQのJSON-LDを画面表示と突き合わせるための、ページ別FAQデータ一覧。
GUIDE_PAGES = [
    ("tabisync:guide_sample", GUIDE_SAMPLE_FAQ),
    ("tabisync:guide_no_signup", GUIDE_NO_SIGNUP_FAQ),
    ("tabisync:guide_collaboration", GUIDE_COLLABORATION_FAQ),
    ("tabisync:guide_all_in_one", GUIDE_ALL_IN_ONE_FAQ),
    ("tabisync:guide_ai_concierge", GUIDE_AI_CONCIERGE_FAQ),
]


class StaticPageTests(TestCase):
    def test_static_pages_return_200(self):
        for url_name in PUBLIC_URL_NAMES:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_offline_and_robots_return_200(self):
        self.assertEqual(self.client.get(reverse("tabisync:offline")).status_code, 200)
        self.assertEqual(self.client.get(reverse("tabisync:robots_txt")).status_code, 200)

    def test_public_pages_have_self_referencing_canonical_and_index_robots(self):
        for url_name in PUBLIC_URL_NAMES:
            with self.subTest(url_name=url_name):
                path = reverse(url_name)
                response = self.client.get(path)
                content = response.content.decode()
                self.assertIn(
                    f'<link rel="canonical" href="{settings.PUBLIC_BASE_URL}{path}">',
                    content,
                )
                self.assertIn('<meta name="robots" content="index, follow">', content)

    def test_canonical_ignores_query_string_and_host_header(self):
        response = self.client.get(
            reverse("tabisync:qa") + "?utm_source=test",
            HTTP_HOST="127.0.0.1",
        )
        content = response.content.decode()
        expected_canonical = f'<link rel="canonical" href="{settings.PUBLIC_BASE_URL}{reverse("tabisync:qa")}">'
        self.assertIn(expected_canonical, content)
        self.assertNotIn("utm_source", content.split('rel="canonical"')[1][:200])

    def test_contact_thanks_offline_and_404_are_noindex_follow(self):
        contact_response = self.client.get(reverse("tabisync:contact"))
        self.assertIn('<meta name="robots" content="noindex, follow">', contact_response.content.decode())

        offline_response = self.client.get(reverse("tabisync:offline"))
        self.assertIn('<meta name="robots" content="noindex, follow">', offline_response.content.decode())

    def test_profile_image_alt_identifies_the_person(self):
        content = self.client.get(reverse("tabisync:profile")).content.decode()

        self.assertIn('alt="TabiSync運営者nagaTの写真"', content)
        self.assertNotIn('alt="運営者プロフィール画像"', content)

    def test_guide_sample_has_clear_link_to_okinawa_demo(self):
        content = self.client.get(reverse("tabisync:guide_sample")).content.decode()

        self.assertIn(
            f'class="guide-sample-link" href="{reverse("tabisync:demo_v2_content")}"',
            content,
        )
        self.assertIn("サンプルしおりを開く", content)
        self.assertIn("沖縄旅行のデモ画面へ移動", content)

    def test_create_page_has_concise_pre_creation_notes(self):
        content = self.client.get(reverse("tabisync:create")).content.decode()

        self.assertIn("作成前の確認", content)
        self.assertIn("開始日と終了日は必須です。最大30日間まで設定できます。", content)
        self.assertIn("閲覧用・編集用パスワードは任意です。", content)
        self.assertIn("作成後の専用URLまたはQRコードで共有できます。", content)
        self.assertNotIn("作成前に確認しておきたいこと", content)

    def test_common_pages_link_to_official_instagram(self):
        instagram_url = "https://www.instagram.com/tabisync_com/"

        for url_name in ["tabisync:home", "tabisync:create"]:
            with self.subTest(url_name=url_name):
                content = self.client.get(reverse(url_name)).content.decode()
                self.assertGreaterEqual(content.count(f'href="{instagram_url}"'), 2)
                self.assertIn('aria-label="TabiSync公式Instagram"', content)
                self.assertIn('class="fa-brands fa-instagram"', content)
                self.assertIn('<nav class="site-footer-social" aria-label="公式SNS">', content)
                self.assertNotIn('<ul class="site-footer-social"', content)

    def test_common_pages_link_to_note_blog(self):
        note_url = "https://note.com/tabisync_com"

        for url_name in ["tabisync:home", "tabisync:create"]:
            with self.subTest(url_name=url_name):
                content = self.client.get(reverse(url_name)).content.decode()
                self.assertEqual(content.count(f'href="{note_url}"'), 2)
                self.assertNotIn("https://blog.tabisync.com", content)

    def test_updates_are_grouped_by_year_in_newest_first_heading_order(self):
        content = self.client.get(reverse("tabisync:updates")).content.decode()
        heading_2026 = '<h2 id="updates-2026" class="user-agreement-sub-title">2026年</h2>'
        heading_2025 = '<h2 id="updates-2025" class="user-agreement-sub-title">2025年</h2>'

        self.assertEqual(content.count("<h1"), 1)
        self.assertEqual(content.count("<h2"), 2)
        self.assertLess(content.index(heading_2026), content.index(heading_2025))

        section_2026 = content.split(heading_2026, 1)[1].split("</section>", 1)[0]
        section_2025 = content.split(heading_2025, 1)[1].split("</section>", 1)[0]
        self.assertIn("2026年08月13日", section_2026)
        self.assertNotIn("2025年", section_2026)
        self.assertIn("2025年06月24日", section_2025)
        self.assertNotIn("2026年", section_2025)

    @override_settings(DEBUG=False)
    def test_404_returns_404_status_with_noindex_and_links_home(self):
        response = self.client.get("/this-path-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        content = response.content.decode()
        self.assertIn("ページが見つかりません", content)
        self.assertIn('<meta name="robots" content="noindex, follow">', content)
        self.assertIn(reverse("tabisync:home"), content)
        self.assertIn(reverse("tabisync:qa"), content)


class RobotsTxtTests(TestCase):
    def test_robots_txt_is_text_plain_and_has_single_sitemap_line(self):
        response = self.client.get(reverse("tabisync:robots_txt"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0], "text/plain")

        body = response.content.decode()
        self.assertTrue(body.endswith("\n"))

        sitemap_lines = [line for line in body.splitlines() if line.startswith("Sitemap:")]
        self.assertEqual(len(sitemap_lines), 1)
        self.assertEqual(
            sitemap_lines[0],
            f"Sitemap: {settings.PUBLIC_BASE_URL}{reverse('django-sitemap')}",
        )

    def test_robots_txt_does_not_disallow_content_or_reset_paths(self):
        body = self.client.get(reverse("tabisync:robots_txt")).content.decode()
        self.assertNotIn("Disallow: /content/", body)
        self.assertNotIn("Disallow: /reset", body)
        self.assertIn("Disallow: /admin/nagat28/", body)


class SitemapTests(TestCase):
    def test_sitemap_only_contains_policy_approved_urls_on_public_origin(self):
        response = self.client.get(reverse("django-sitemap"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()

        expected_locs = {
            f"{settings.PUBLIC_BASE_URL}{reverse(name)}" for name in PUBLIC_URL_NAMES
        }
        found_locs = set(_extract_locs(body))
        self.assertEqual(found_locs, expected_locs)

        # contactはindexだが、内容拡充までサイトマップには含めない。
        self.assertNotIn(f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:contact')}", found_locs)

    def test_sitemap_urls_return_200_and_match_canonical(self):
        response = self.client.get(reverse("django-sitemap"))
        for loc in _extract_locs(response.content.decode()):
            path = loc[len(settings.PUBLIC_BASE_URL):]
            with self.subTest(path=path):
                page_response = self.client.get(path)
                self.assertEqual(page_response.status_code, 200)
                self.assertIn(f'<link rel="canonical" href="{loc}">', page_response.content.decode())

    def test_all_sitemap_pages_have_valid_non_future_lastmod(self):
        body = self.client.get(reverse("django-sitemap")).content.decode()
        self.assertEqual(set(SITEMAP_TEMPLATE_PATHS), set(SITEMAP_URL_NAMES))

        for url_name in SITEMAP_URL_NAMES:
            with self.subTest(url_name=url_name):
                loc = f"{settings.PUBLIC_BASE_URL}{reverse(url_name)}"
                entry = body.split(f"<loc>{loc}</loc>")[1].split("</url>")[0]
                lastmod = entry.split("<lastmod>")[1].split("</lastmod>")[0]
                parsed_lastmod = date.fromisoformat(lastmod)
                self.assertLessEqual(parsed_lastmod, date.today())

    def test_lastmod_returns_none_when_template_is_missing_or_inaccessible(self):
        sitemap = StaticViewSitemap()

        with TemporaryDirectory() as empty_base_dir:
            with override_settings(BASE_DIR=Path(empty_base_dir)):
                self.assertIsNone(sitemap.lastmod("tabisync:home"))

        with patch("tabisync.sitemaps.Path.stat", side_effect=OSError):
            self.assertIsNone(sitemap.lastmod("tabisync:home"))

        self.assertIsNone(sitemap.lastmod("tabisync:not-mapped"))


class OgpImageTests(TestCase):
    PAGE_IMAGES = [
        (
            "tabisync:guide_sample",
            "img/ogp-guide-sample.webp",
            "沖縄旅行のサンプルしおりと作成手順を表すイラスト",
        ),
        (
            "tabisync:guide_no_signup",
            "img/ogp-guide-no-signup.webp",
            "登録不要で旅行しおりを安全に共有する流れを表すイラスト",
        ),
        (
            "tabisync:guide_collaboration",
            "img/ogp-guide-collaboration.webp",
            "友達や家族が一つの旅行計画を共同編集する様子のイラスト",
        ),
        (
            "tabisync:guide_all_in_one",
            "img/ogp-guide-all-in-one.webp",
            "旅程・地図・持ち物・メモを一つの旅行しおりにまとめたイラスト",
        ),
        (
            "tabisync:guide_ai_concierge",
            "img/ogp-guide-ai-concierge.webp",
            "AIコンシェルジュが旅行計画の改善を提案する様子のイラスト",
        ),
        (
            "tabisync:qa",
            "img/ogp-faq.webp",
            "旅行しおりの作成・共有・安全性に関する質問を表すイラスト",
        ),
        (
            "tabisync:profile",
            "img/ogp-profile.webp",
            "旅の記録をもとに旅行しおりサービスを開発する運営者のイラスト",
        ),
    ]

    def test_pages_use_matching_absolute_og_and_twitter_images(self):
        for url_name, static_path, alt_text in self.PAGE_IMAGES:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                content = response.content.decode()
                image_url = f"{settings.PUBLIC_BASE_URL}{staticfiles_storage.url(static_path)}"

                self.assertEqual(response.status_code, 200)
                self.assertIn(f'<meta property="og:image" content="{image_url}">', content)
                self.assertIn(f'<meta name="twitter:image" content="{image_url}">', content)
                self.assertIn(f'<meta property="og:image:alt" content="{alt_text}">', content)

    def test_ogp_images_are_servable_webp_files_with_expected_dimensions(self):
        request_factory = RequestFactory()

        for _, static_path, _ in self.PAGE_IMAGES:
            with self.subTest(static_path=static_path):
                response = serve_static(
                    request_factory.get(f"{settings.STATIC_URL}{static_path}"),
                    static_path,
                    insecure=True,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "image/webp")

                file_path = finders.find(static_path)
                self.assertIsNotNone(file_path)
                with Image.open(file_path) as image:
                    self.assertEqual(image.size, (1200, 630))


def _extract_locs(sitemap_xml):
    return [
        segment.split("</loc>")[0]
        for segment in sitemap_xml.split("<loc>")[1:]
    ]


class FaqStructuredDataTests(TestCase):
    def test_faq_json_ld_matches_visible_questions_and_answers(self):
        response = self.client.get(reverse("tabisync:qa"))
        content = response.content.decode()

        json_ld_raw = content.split(
            '<script type="application/ld+json">'
        )[1].split("</script>")[0]
        data = json.loads(json_ld_raw)

        self.assertEqual(data["@context"], "https://schema.org")
        graph_types = {node["@type"] for node in data["@graph"]}
        self.assertEqual(graph_types, {"BreadcrumbList", "FAQPage"})

        faq_node = next(node for node in data["@graph"] if node["@type"] == "FAQPage")
        breadcrumb_node = next(
            node for node in data["@graph"] if node["@type"] == "BreadcrumbList"
        )

        expected_pairs = [
            (item["question"], item["answer"])
            for section in FAQ_SECTIONS
            for item in section["questions"]
        ]
        actual_pairs = [
            (entry["name"], entry["acceptedAnswer"]["text"])
            for entry in faq_node["mainEntity"]
        ]
        self.assertEqual(actual_pairs, expected_pairs)

        self.assertEqual(
            [item["name"] for item in breadcrumb_node["itemListElement"]],
            ["ホーム", "よくある質問"],
        )
        self.assertEqual(
            breadcrumb_node["itemListElement"][0]["item"],
            f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:home')}",
        )
        self.assertEqual(
            breadcrumb_node["itemListElement"][1]["item"],
            f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:qa')}",
        )
        self.assertIn('aria-label="パンくずリスト"', content)
        self.assertIn('aria-current="page">よくある質問</span>', content)

        for question, answer in expected_pairs:
            self.assertIn(question, content)
            self.assertIn(answer, content)


class HomeStructuredDataTests(TestCase):
    def test_home_json_ld_is_valid_and_uses_public_base_url(self):
        response = self.client.get(reverse("tabisync:home"))
        content = response.content.decode()

        json_ld_raw = content.split(
            '<script type="application/ld+json">'
        )[1].split("</script>")[0]
        data = json.loads(json_ld_raw)

        self.assertEqual(data["@context"], "https://schema.org")
        types = {node["@type"] for node in data["@graph"]}
        self.assertEqual(types, {"WebSite", "Organization", "SoftwareApplication"})

        organization = next(node for node in data["@graph"] if node["@type"] == "Organization")
        self.assertEqual(
            organization["url"],
            f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:home')}",
        )
        self.assertEqual(
            set(organization["sameAs"]),
            {
                "https://www.instagram.com/tabisync_com/",
                "https://note.com/tabisync_com",
                "https://x.com/tabisync_com",
            },
        )


class GuidePageContentTests(TestCase):
    """Task 005で追加した検索意図別ページと、拡充したしおり作成ページを検証する。"""

    def test_guide_pages_and_create_page_have_single_h1(self):
        for url_name in [name for name, _ in GUIDE_PAGES] + ["tabisync:create"]:
            with self.subTest(url_name=url_name):
                content = self.client.get(reverse(url_name)).content.decode()
                self.assertEqual(content.count("<h1"), 1)

    def test_guide_pages_faq_json_ld_matches_visible_questions_and_answers(self):
        for url_name, faq_items in GUIDE_PAGES:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                content = response.content.decode()
                json_ld_raw = content.split(
                    '<script type="application/ld+json">'
                )[1].split("</script>")[0]
                data = json.loads(json_ld_raw)

                self.assertEqual(data["@context"], "https://schema.org")
                graph_types = {node["@type"] for node in data["@graph"]}
                self.assertEqual(graph_types, {"BreadcrumbList", "FAQPage"})

                faq_node = next(node for node in data["@graph"] if node["@type"] == "FAQPage")
                expected_pairs = [(item["question"], item["answer"]) for item in faq_items]
                actual_pairs = [
                    (entry["name"], entry["acceptedAnswer"]["text"])
                    for entry in faq_node["mainEntity"]
                ]
                self.assertEqual(actual_pairs, expected_pairs)

                for question, answer in expected_pairs:
                    self.assertIn(question, content)
                    self.assertIn(answer, content)

    def test_guide_pages_breadcrumb_json_ld_matches_visible_breadcrumb(self):
        for url_name, _ in GUIDE_PAGES:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                content = response.content.decode()
                json_ld_raw = content.split(
                    '<script type="application/ld+json">'
                )[1].split("</script>")[0]
                data = json.loads(json_ld_raw)

                breadcrumb_node = next(node for node in data["@graph"] if node["@type"] == "BreadcrumbList")
                self.assertEqual(breadcrumb_node["itemListElement"][0]["name"], "ホーム")
                self.assertEqual(
                    breadcrumb_node["itemListElement"][0]["item"],
                    f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:home')}",
                )
                self.assertIn('aria-current="page"', content)

    def test_create_page_has_breadcrumb_json_ld_and_body_content(self):
        response = self.client.get(reverse("tabisync:create"))
        content = response.content.decode()

        json_ld_raw = content.split(
            '<script type="application/ld+json">'
        )[1].split("</script>")[0]
        data = json.loads(json_ld_raw)
        self.assertEqual(data["@graph"][0]["@type"], "BreadcrumbList")
        self.assertIn('aria-current="page"', content)
        self.assertIn("開始日と終了日は必須です。最大30日間まで設定できます。", content)


class XRobotsTagAuditTests(TestCase):
    """UUID付きしおり・認証・リセット系レスポンスに一貫してnoindexヘッダーが付くことを監査する。"""

    def setUp(self):
        self.itinerary = Itinerary.objects.create(title="Test Trip")
        self.itinerary.set_passwords(view_pw="", edit_pw="")
        self.itinerary.save()

    def _assert_noindex(self, response):
        self.assertEqual(response.get("X-Robots-Tag"), "noindex, nofollow")

    def test_content_v2_view_is_noindex(self):
        url = reverse("tabisync:content_v2", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        self._assert_noindex(self.client.get(url))

    def test_legacy_content_view_is_noindex(self):
        url = reverse("tabisync:content", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        self._assert_noindex(self.client.get(url))

    def test_memo_and_list_v1_views_are_noindex(self):
        memo_url = reverse("tabisync:content_memo", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        list_url = reverse("tabisync:content_list", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        self._assert_noindex(self.client.get(memo_url))
        self._assert_noindex(self.client.get(list_url))

    def test_password_view_is_noindex_on_get_and_post(self):
        url = reverse("tabisync:content_password", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        self._assert_noindex(self.client.get(url))

    def test_legacy_edit_view_is_noindex(self):
        url = reverse("tabisync:edit", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        self._assert_noindex(self.client.get(url))
