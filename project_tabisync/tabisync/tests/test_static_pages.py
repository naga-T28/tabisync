from django.test import TestCase
from django.urls import reverse


class StaticPageTests(TestCase):
    def test_static_pages_return_200(self):
        url_names = [
            "tabisync:home",
            "tabisync:qa",
            "tabisync:profile",
            "tabisync:user_agreement",
            "tabisync:concierge_terms",
            "tabisync:privacy_policy",
            "tabisync:updates",
        ]
        for url_name in url_names:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_offline_and_robots_return_200(self):
        self.assertEqual(self.client.get(reverse("tabisync:offline")).status_code, 200)
        self.assertEqual(self.client.get(reverse("tabisync:robots_txt")).status_code, 200)
