import json
import socket
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from ..concierge_agent.link_preview import MAX_LINK_PREVIEW_URLS_PER_REQUEST, _is_public_hostname
from ..models import Itinerary


def _addrinfo(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


class LinkPreviewHostGuardTests(SimpleTestCase):
    def test_rejects_loopback(self):
        with patch("socket.getaddrinfo", return_value=_addrinfo("127.0.0.1")):
            self.assertFalse(_is_public_hostname("localhost"))

    def test_rejects_link_local_metadata_ip(self):
        with patch("socket.getaddrinfo", return_value=_addrinfo("169.254.169.254")):
            self.assertFalse(_is_public_hostname("metadata.internal"))

    def test_rejects_private_range(self):
        with patch("socket.getaddrinfo", return_value=_addrinfo("10.0.0.5")):
            self.assertFalse(_is_public_hostname("internal.example"))

    def test_accepts_public_ip(self):
        with patch("socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
            self.assertTrue(_is_public_hostname("example.com"))

    def test_rejects_when_dns_fails(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror):
            self.assertFalse(_is_public_hostname("does-not-exist.invalid"))


class ConciergeLinkPreviewsViewTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Trip", start_date=date(2026, 1, 1), end_date=date(2026, 1, 3),
        )
        self.url = reverse(
            "tabisync:V2_concierge_link_previews", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def _post(self, urls):
        return self.client.post(
            self.url,
            data=json.dumps({"urls": urls}),
            content_type="application/json",
        )

    @patch("tabisync.views.concierge.get_link_preview")
    def test_returns_preview_for_each_valid_url(self, mock_get_preview):
        mock_get_preview.side_effect = lambda url: {
            "url": url, "domain": "example.com", "title": "t", "image": None, "site_name": None,
        }

        response = self._post(["https://example.com/a", "https://example.com/b"])

        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(len(data["previews"]), 2)
        self.assertEqual(mock_get_preview.call_count, 2)

    @patch("tabisync.views.concierge.get_link_preview")
    def test_ignores_invalid_schemes_and_dedupes(self, mock_get_preview):
        mock_get_preview.return_value = {
            "url": "https://example.com", "domain": "example.com", "title": None, "image": None, "site_name": None,
        }

        response = self._post([
            "javascript:alert(1)",
            "https://example.com",
            "https://example.com",
            "not-a-url",
        ])

        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["previews"]), 1)
        mock_get_preview.assert_called_once_with("https://example.com")

    @patch("tabisync.views.concierge.get_link_preview")
    def test_caps_url_count_per_request(self, mock_get_preview):
        mock_get_preview.side_effect = lambda url: {
            "url": url, "domain": "example.com", "title": None, "image": None, "site_name": None,
        }
        urls = [f"https://example.com/{i}" for i in range(MAX_LINK_PREVIEW_URLS_PER_REQUEST + 3)]

        response = self._post(urls)

        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["previews"]), MAX_LINK_PREVIEW_URLS_PER_REQUEST)

    def test_rejects_non_list_urls(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"urls": "https://example.com"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_requires_view_access_when_password_set(self):
        self.itinerary.view_password = "hashed-not-empty"
        self.itinerary.save(update_fields=["view_password"])

        response = self._post(["https://example.com"])
        self.assertEqual(response.status_code, 403)
