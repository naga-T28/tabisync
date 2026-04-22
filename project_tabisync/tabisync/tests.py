from django.test import RequestFactory, TestCase

from .views import get_client_ip, ratelimit_client_ip


class ClientIpTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_client_ip_prefers_cloudflare_header(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.10, 10.0.0.1",
            HTTP_CF_CONNECTING_IP="203.0.113.10",
        )

        self.assertEqual(get_client_ip(request), "203.0.113.10")

    def test_get_client_ip_falls_back_to_first_forwarded_ip(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.10, 10.0.0.1",
        )

        self.assertEqual(get_client_ip(request), "198.51.100.10")

    def test_ratelimit_client_ip_uses_same_resolution(self):
        request = self.factory.get("/", REMOTE_ADDR="198.51.100.10")

        self.assertEqual(ratelimit_client_ip(None, request), "198.51.100.10")
