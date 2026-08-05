from datetime import date

from django.test import TestCase
from django.urls import reverse

from ..models import Itinerary, Schedule, TravelDate
from ..views.legacy_v1 import get_travel_date_range_context, prepare_travel_dates_with_schedules


class TravelDateHelperTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(title="Test Trip")

    def test_get_travel_date_range_context_empty(self):
        context = get_travel_date_range_context(self.itinerary.travel_dates.all())
        self.assertIsNone(context["first_date_str"])
        self.assertIsNone(context["last_date_str"])

    def test_get_travel_date_range_context_with_dates(self):
        TravelDate.objects.create(itinerary=self.itinerary, date=date(2026, 1, 1), order=0)
        TravelDate.objects.create(itinerary=self.itinerary, date=date(2026, 1, 3), order=1)

        context = get_travel_date_range_context(self.itinerary.travel_dates.all())
        self.assertEqual(context["first_date_str"], "2026.01.01")
        self.assertEqual(context["last_date_str"], "2026.01.03")

    def test_prepare_travel_dates_with_schedules_attaches_sorted_schedules(self):
        travel_date = TravelDate.objects.create(itinerary=self.itinerary, date=date(2026, 1, 1), order=0)
        Schedule.objects.create(travel_date=travel_date, title="夕食", location="", start_time="18:00")
        Schedule.objects.create(travel_date=travel_date, title="朝食", location="", start_time="08:00")

        travel_dates = prepare_travel_dates_with_schedules(self.itinerary)
        titles = [s.title for s in travel_dates[0].sorted_schedules]
        self.assertEqual(titles, ["朝食", "夕食"])


class ItineraryDetailViewTests(TestCase):
    def test_get_returns_200_without_password(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        url = reverse("tabisync:content", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_get_redirects_when_password_protected(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        itinerary.set_passwords(view_pw="secret", edit_pw="")
        itinerary.save()

        url = reverse("tabisync:content", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class MemoDetailViewTests(TestCase):
    def test_get_returns_200(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        url = reverse("tabisync:content_memo", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ListDetailViewTests(TestCase):
    def test_get_returns_200(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        url = reverse("tabisync:content_list", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class EditViewTests(TestCase):
    def test_get_returns_200_without_edit_password(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        url = reverse("tabisync:edit", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
