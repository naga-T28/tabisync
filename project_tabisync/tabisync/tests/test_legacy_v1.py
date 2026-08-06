from datetime import date, timedelta

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

    def test_prepare_travel_dates_with_schedules_orders_schedules_by_start_time(self):
        travel_date = TravelDate.objects.create(itinerary=self.itinerary, date=date(2026, 1, 1), order=0)
        Schedule.objects.create(travel_date=travel_date, title="夕食", location="", start_time="18:00")
        Schedule.objects.create(travel_date=travel_date, title="朝食", location="", start_time="08:00")

        travel_dates = prepare_travel_dates_with_schedules(self.itinerary)
        titles = [s.title for s in travel_dates[0].schedules.all()]
        self.assertEqual(titles, ["朝食", "夕食"])

    def test_prepare_travel_dates_with_schedules_does_not_scale_with_travel_date_count(self):
        # travel_date/scheduleの件数を増やしても、prefetch_relatedにより
        # クエリ数が一定であること（N+1が発生していないこと）を確認する。
        def build_itinerary_with_days(day_count):
            itinerary = Itinerary.objects.create(title=f"Trip-{day_count}")
            for i in range(day_count):
                travel_date = TravelDate.objects.create(
                    itinerary=itinerary, date=date(2026, 1, 1) + timedelta(days=i), order=i
                )
                Schedule.objects.create(
                    travel_date=travel_date, title=f"予定{i}", location="", start_time="09:00"
                )
            return itinerary

        small_itinerary = build_itinerary_with_days(1)
        large_itinerary = build_itinerary_with_days(5)

        with self.assertNumQueries(2):
            list(prepare_travel_dates_with_schedules(small_itinerary))

        with self.assertNumQueries(2):
            result = list(prepare_travel_dates_with_schedules(large_itinerary))
            for travel_date in result:
                list(travel_date.schedules.all())


class ItineraryDetailViewTests(TestCase):
    def test_get_returns_200_without_password(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        url = reverse("tabisync:content", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_display_query_count_does_not_scale_with_day_count(self):
        # 表示クエリ数が日数・予定数に比例してN+1にならないことを確認する。
        def build_itinerary_with_days(day_count):
            itinerary = Itinerary.objects.create(title=f"Trip-{day_count}")
            for i in range(day_count):
                travel_date = TravelDate.objects.create(
                    itinerary=itinerary, date=date(2026, 1, 1) + timedelta(days=i), order=i
                )
                Schedule.objects.create(
                    travel_date=travel_date, title=f"予定{i}", location="", start_time="09:00"
                )
            return itinerary

        small_itinerary = build_itinerary_with_days(1)
        large_itinerary = build_itinerary_with_days(5)

        small_url = reverse("tabisync:content", kwargs={"pk": small_itinerary.pk, "token": small_itinerary.token})
        large_url = reverse("tabisync:content", kwargs={"pk": large_itinerary.pk, "token": large_itinerary.token})

        with self.assertNumQueries(3):
            self.client.get(small_url)

        with self.assertNumQueries(3):
            self.client.get(large_url)

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
