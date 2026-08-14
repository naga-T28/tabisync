from django.test import TestCase, override_settings
from django.urls import reverse

from ..models import Itinerary


class NonProductionNoIndexMiddlewareTests(TestCase):
    def test_non_production_environments_force_noindex_on_all_responses(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        private_url = reverse(
            "tabisync:content_password",
            kwargs={"pk": itinerary.pk, "token": itinerary.token},
        )

        for environment in ("", "staging", "development"):
            with self.subTest(environment=environment), self.settings(
                ENVIRONMENT=environment,
                IS_PRODUCTION=False,
            ):
                public_response = self.client.get(reverse("tabisync:home"))
                private_response = self.client.get(private_url)
                self.assertEqual(public_response["X-Robots-Tag"], "noindex, nofollow")
                self.assertEqual(private_response["X-Robots-Tag"], "noindex, nofollow")

    @override_settings(ENVIRONMENT="production", IS_PRODUCTION=True)
    def test_production_does_not_add_header_to_public_page(self):
        response = self.client.get(reverse("tabisync:home"))
        self.assertNotIn("X-Robots-Tag", response)

    @override_settings(ENVIRONMENT="production", IS_PRODUCTION=True)
    def test_production_preserves_existing_noindex_header(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        response = self.client.get(reverse(
            "tabisync:content_password",
            kwargs={"pk": itinerary.pk, "token": itinerary.token},
        ))
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    @override_settings(
        ENVIRONMENT="staging",
        IS_PRODUCTION=False,
        PUBLIC_BASE_URL="https://staging.tabisync.com",
    )
    def test_non_production_header_does_not_change_canonical_or_sitemap_origin(self):
        home_path = reverse("tabisync:home")
        home_response = self.client.get(home_path)
        self.assertContains(
            home_response,
            f'<link rel="canonical" href="https://staging.tabisync.com{home_path}">',
            html=True,
        )

        sitemap_response = self.client.get(reverse("django-sitemap"))
        self.assertContains(
            sitemap_response,
            f"<loc>https://staging.tabisync.com{home_path}</loc>",
        )
