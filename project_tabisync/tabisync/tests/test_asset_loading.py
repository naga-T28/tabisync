import shutil
import tempfile
from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from ..models import Itinerary, TravelDate


class FlatpickrRemovalTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.itinerary_kwargs = {
            "pk": self.itinerary.pk,
            "token": self.itinerary.token,
        }
        TravelDate.objects.create(
            itinerary=self.itinerary,
            date=date(2026, 1, 1),
            order=0,
        )

    def test_all_previously_affected_pages_render_without_flatpickr(self):
        urls = [
            reverse("tabisync:qa"),
            reverse("tabisync:content_password", kwargs=self.itinerary_kwargs),
            reverse("tabisync:content", kwargs=self.itinerary_kwargs),
            reverse("tabisync:content_memo", kwargs=self.itinerary_kwargs),
            reverse("tabisync:content_list", kwargs=self.itinerary_kwargs),
            reverse("tabisync:edit", kwargs=self.itinerary_kwargs),
            reverse("tabisync:Wantto", kwargs=self.itinerary_kwargs),
            reverse("tabisync:V2_concierge", kwargs=self.itinerary_kwargs),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("flatpickr", response.content.decode().lower())

    def test_create_and_edit_forms_keep_native_date_inputs(self):
        urls_and_minimum_counts = [
            (reverse("tabisync:create"), 2),
            (reverse("tabisync:edit", kwargs=self.itinerary_kwargs), 1),
            (reverse("tabisync:content_edit_form_v2", kwargs=self.itinerary_kwargs), 2),
        ]

        for url, minimum_count in urls_and_minimum_counts:
            with self.subTest(url=url):
                response = self.client.get(url)
                content = response.content.decode()
                self.assertEqual(response.status_code, 200)
                self.assertGreaterEqual(content.count('type="date"'), minimum_count)
                self.assertNotIn("flatpickr", content.lower())


_FONT_AWESOME_MEDIA_ROOT = tempfile.mkdtemp(prefix="tabisync-test-font-awesome-media-")


@override_settings(MEDIA_ROOT=_FONT_AWESOME_MEDIA_ROOT)
class FontAwesomeLoadingTests(TestCase):
    FONT_AWESOME_URL = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_FONT_AWESOME_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.itinerary_kwargs = {
            "pk": self.itinerary.pk,
            "token": self.itinerary.token,
        }

    def _assert_async_font_awesome(self, response):
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f'<link rel="preload" href="{self.FONT_AWESOME_URL}" as="style"',
            content,
        )
        self.assertIn("this.onload=null;this.rel='stylesheet'", content)
        self.assertIn(
            f'<noscript>\n    <link rel="stylesheet" href="{self.FONT_AWESOME_URL}">\n</noscript>',
            content,
        )

    def test_representative_pages_use_async_font_awesome_with_fallback(self):
        urls = [
            reverse("tabisync:home"),
            reverse("tabisync:qa"),
            reverse("tabisync:content_password", kwargs=self.itinerary_kwargs),
            reverse("tabisync:demo_v2_content"),
            reverse("tabisync:demo_v2_concierge"),
            reverse("tabisync:content", kwargs=self.itinerary_kwargs),
            reverse("tabisync:content_memo", kwargs=self.itinerary_kwargs),
            reverse("tabisync:content_list", kwargs=self.itinerary_kwargs),
            reverse("tabisync:edit", kwargs=self.itinerary_kwargs),
            reverse("tabisync:Wantto", kwargs=self.itinerary_kwargs),
            reverse("tabisync:V2_concierge", kwargs=self.itinerary_kwargs),
            reverse(
                "tabisync:blog_schedule_embed",
                kwargs={
                    "pk": self.itinerary.pk,
                    "open_token": self.itinerary.blog_embed_token,
                    "day": 1,
                },
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                self._assert_async_font_awesome(self.client.get(url))

    def test_dynamic_blog_embed_tag_uses_same_non_blocking_pattern(self):
        response = self.client.get(reverse("tabisync:content_v2", kwargs=self.itinerary_kwargs))
        content = response.content.decode()
        self.assertIn("const blogFontAwesomeTag = `<link rel=", content)
        self.assertIn(f'href="{self.FONT_AWESOME_URL}" as="style"', content)


class ImageDimensionTests(TestCase):
    def test_home_hero_and_header_logo_have_intrinsic_dimensions(self):
        response = self.client.get(reverse("tabisync:home"))
        content = response.content.decode()
        self.assertIn(
            'class="home-hero-product-image" width="4167" height="3125" fetchpriority="high"',
            content,
        )
        self.assertIn(
            'class="logo-image" width="500" height="112"',
            content,
        )

    def test_standard_and_noindex_base_logos_have_intrinsic_dimensions(self):
        standard = self.client.get(reverse("tabisync:qa")).content.decode()
        self.assertIn('class="logo-image" width="500" height="112"', standard)

        itinerary = Itinerary.objects.create(title="Test Trip")
        noindex = self.client.get(reverse(
            "tabisync:content_password",
            kwargs={"pk": itinerary.pk, "token": itinerary.token},
        )).content.decode()
        self.assertIn('class="logo-image" width="1500" height="300"', noindex)

    def test_404_image_has_intrinsic_dimensions(self):
        with self.settings(DEBUG=False):
            response = self.client.get("/missing-image-dimension-test/")
        self.assertEqual(response.status_code, 404)
        self.assertIn(
            'class="img-404" width="2144" height="1196"',
            response.content.decode(),
        )


class GoogleFontsLoadingTests(TestCase):
    COMBINED_FONT_URL = (
        "https://fonts.googleapis.com/css2?"
        "family=Source+Sans+Pro:wght@400;600;700&amp;"
        "family=Noto+Sans+JP:wght@400;500;600;700;750;800;900&amp;display=swap"
    )

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.itinerary_kwargs = {
            "pk": self.itinerary.pk,
            "token": self.itinerary.token,
        }

    def test_representative_pages_use_one_combined_source_and_noto_request(self):
        urls = [
            reverse("tabisync:home"),
            reverse("tabisync:qa"),
            reverse("tabisync:content_password", kwargs=self.itinerary_kwargs),
            reverse("tabisync:demo_v2_content"),
            reverse("tabisync:demo_v2_concierge"),
            reverse("tabisync:content", kwargs=self.itinerary_kwargs),
            reverse("tabisync:content_memo", kwargs=self.itinerary_kwargs),
            reverse("tabisync:content_list", kwargs=self.itinerary_kwargs),
            reverse("tabisync:edit", kwargs=self.itinerary_kwargs),
            reverse("tabisync:Wantto", kwargs=self.itinerary_kwargs),
            reverse("tabisync:V2_concierge", kwargs=self.itinerary_kwargs),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                content = response.content.decode()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(content.count(self.COMBINED_FONT_URL), 1)
                self.assertNotIn("Noto+Sans+JP:wght@100..900", content)

    def test_blog_embed_keeps_single_family_but_uses_only_required_weights(self):
        response = self.client.get(reverse(
            "tabisync:blog_schedule_embed",
            kwargs={
                "pk": self.itinerary.pk,
                "open_token": self.itinerary.blog_embed_token,
                "day": 1,
            },
        ))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "family=Noto+Sans+JP:wght@400;500;600;700;750;800;900&amp;display=swap",
            content,
        )
        self.assertNotIn("Noto+Sans+JP:wght@100..900", content)
