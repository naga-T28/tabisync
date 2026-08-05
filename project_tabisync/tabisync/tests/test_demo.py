from django.test import TestCase
from django.urls import reverse


class DemoPageTests(TestCase):
    def test_demo_pages_return_200(self):
        url_names = [
            "tabisync:demo_content",
            "tabisync:demo_edit",
            "tabisync:demo_list",
            "tabisync:demo_memo",
            "tabisync:demo_v2_content",
            "tabisync:demo_v2_memo",
            "tabisync:demo_v2_list",
            "tabisync:demo_v2_map",
            "tabisync:demo_v2_edit",
            "tabisync:demo_v2_concierge",
        ]
        for url_name in url_names:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
