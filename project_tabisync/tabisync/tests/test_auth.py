from unittest.mock import patch

from django.core import mail, signing
from django.test import TestCase, override_settings
from django.urls import reverse

from ..models import Itinerary
from ..views.access_control import build_view_session_key


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ItineraryPasswordViewTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(title="Test Trip")
        self.itinerary.set_passwords(view_pw="secret123", edit_pw="")
        self.itinerary.save()
        self.url = reverse(
            "tabisync:content_password",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch("tabisync.views.auth.verify_turnstile", return_value=True)
    def test_post_with_correct_password_redirects(self, _mock_turnstile):
        response = self.client.post(self.url, {"view_password": "secret123"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get(build_view_session_key(self.itinerary)))

    @patch("tabisync.views.auth.verify_turnstile", return_value=True)
    def test_post_with_wrong_password_shows_error(self, _mock_turnstile):
        response = self.client.post(self.url, {"view_password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get(build_view_session_key(self.itinerary)))


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.com",
    CONTACT_RECEIVER_EMAIL="receiver@example.com",
)
class ContactFormViewTests(TestCase):
    def test_get_returns_200(self):
        response = self.client.get(reverse("tabisync:contact"))
        self.assertEqual(response.status_code, 200)

    @patch("tabisync.views.auth.verify_turnstile", return_value=True)
    def test_post_valid_form_sends_two_emails(self, _mock_turnstile):
        response = self.client.post(reverse("tabisync:contact"), {
            "email": "user@example.com",
            "name": "テスト太郎",
            "subject": "お問い合わせ",
            "message": "テストメッセージです。",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ResetPasswordViewTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(title="Test Trip")

    def test_get_with_valid_token_returns_200(self):
        signed_token = signing.dumps(
            {"pk": self.itinerary.pk, "token": str(self.itinerary.token), "type": "view"},
            salt="tabisync-password-reset",
        )
        url = reverse("tabisync:reset_password", kwargs={"signed_token": signed_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_get_with_invalid_token_returns_404(self):
        url = reverse("tabisync:reset_password", kwargs={"signed_token": "invalid-token"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_post_sets_new_view_password(self):
        signed_token = signing.dumps(
            {"pk": self.itinerary.pk, "token": str(self.itinerary.token), "type": "view"},
            salt="tabisync-password-reset",
        )
        url = reverse("tabisync:reset_password", kwargs={"signed_token": signed_token})
        response = self.client.post(url, {"password": "new-secret"})

        self.assertEqual(response.status_code, 302)
        self.itinerary.refresh_from_db()
        self.assertTrue(self.itinerary.check_view_password("new-secret"))
