import json

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from ..content_data import FAQ_SECTIONS
from ..models import Itinerary


PUBLIC_URL_NAMES = [
    "tabisync:home",
    "tabisync:qa",
    "tabisync:profile",
    "tabisync:user_agreement",
    "tabisync:concierge_terms",
    "tabisync:privacy_policy",
    "tabisync:updates",
]

# サイトマップに含まれない公開ページ(現状は薄いフォームページのため対象外)。
PUBLIC_BUT_NOT_SITEMAPPED_URL_NAMES = [
    "tabisync:create",
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
        for url_name in PUBLIC_URL_NAMES + PUBLIC_BUT_NOT_SITEMAPPED_URL_NAMES:
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

        # create/contactはindexだが、内容拡充までサイトマップには含めない。
        self.assertNotIn(f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:create')}", found_locs)
        self.assertNotIn(f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:contact')}", found_locs)

    def test_sitemap_urls_return_200_and_match_canonical(self):
        response = self.client.get(reverse("django-sitemap"))
        for loc in _extract_locs(response.content.decode()):
            path = loc[len(settings.PUBLIC_BASE_URL):]
            with self.subTest(path=path):
                page_response = self.client.get(path)
                self.assertEqual(page_response.status_code, 200)
                self.assertIn(f'<link rel="canonical" href="{loc}">', page_response.content.decode())

    def test_updates_page_has_lastmod(self):
        body = self.client.get(reverse("django-sitemap")).content.decode()
        updates_loc = f"{settings.PUBLIC_BASE_URL}{reverse('tabisync:updates')}"
        entry = body.split(f"<loc>{updates_loc}</loc>")[1].split("</url>")[0]
        self.assertIn("<lastmod>", entry)


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

        self.assertEqual(data["@type"], "FAQPage")

        expected_pairs = [
            (item["question"], item["answer"])
            for section in FAQ_SECTIONS
            for item in section["questions"]
        ]
        actual_pairs = [
            (entry["name"], entry["acceptedAnswer"]["text"])
            for entry in data["mainEntity"]
        ]
        self.assertEqual(actual_pairs, expected_pairs)

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
            {"https://blog.tabisync.com", "https://x.com/tabisync_com"},
        )


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
