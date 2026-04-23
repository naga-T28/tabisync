from django.test import RequestFactory, TestCase

from .views import build_public_service_error_message, get_client_ip, ratelimit_client_ip


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

    def test_get_client_ip_ignores_invalid_proxy_headers(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="198.51.100.10",
            HTTP_X_FORWARDED_FOR="unknown, 198.51.100.20",
            HTTP_CF_CONNECTING_IP="not-an-ip",
        )

        self.assertEqual(get_client_ip(request), "198.51.100.20")


class PublicErrorMessageTests(TestCase):
    def test_public_error_message_hides_detail_outside_debug(self):
        with self.settings(DEBUG=False):
            self.assertEqual(
                build_public_service_error_message(Exception("OpenAI API timeout after 8s"), "fallback"),
                "現在アクセスが集中しています。しばらくしてから再度お試しください。",
            )

    def test_public_error_message_keeps_detail_in_debug(self):
        with self.settings(DEBUG=True):
            self.assertEqual(
                build_public_service_error_message(Exception("debug detail"), "fallback"),
                "debug detail",
            )
