import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from ..models import Itinerary

_MEDIA_ROOT = tempfile.mkdtemp(prefix="tabisync-test-media-")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class CreateViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def test_get_renders_form(self):
        response = self.client.get(reverse("tabisync:create"))
        self.assertEqual(response.status_code, 200)

    def test_post_creates_itinerary_and_redirects(self):
        response = self.client.post(reverse("tabisync:create"), {
            "title": "沖縄旅行",
            "subtitle": "",
            "description": "",
            "start_date": "2026-03-01",
            "end_date": "2026-03-03",
            "design_number": "1",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Itinerary.objects.count(), 1)
        self.assertEqual(Itinerary.objects.get().title, "沖縄旅行")

    def test_post_rejects_missing_dates(self):
        response = self.client.post(reverse("tabisync:create"), {"title": "旅行"})
        self.assertEqual(response.status_code, 400)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ItineraryDetailV2ViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        from datetime import date

        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )

    def test_get_returns_200_without_password(self):
        url = reverse("tabisync:content_v2", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_get_redirects_when_password_protected(self):
        self.itinerary.set_passwords(view_pw="secret", edit_pw="")
        self.itinerary.save()

        url = reverse("tabisync:content_v2", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class EditMenuV2ViewTests(TestCase):
    def test_get_returns_200_without_edit_password(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        url = reverse("tabisync:content_edit_v2", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
