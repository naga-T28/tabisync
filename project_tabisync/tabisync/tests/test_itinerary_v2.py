import json
import shutil
import tempfile
from datetime import date, time

from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from ..models import Itinerary, ScheduleV2, WantToGo

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


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ScheduleMapDataTests(TestCase):
    """Task 003: 選択日の訪問スポット地図用データ(schedule_map_data)の回帰テスト。"""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.url = reverse("tabisync:content_v2", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})

    def _get_schedule_map_data(self, response):
        content = response.content.decode("utf-8")
        start = content.index('<script id="schedule-map-data"')
        start = content.index(">", start) + 1
        end = content.index("</script>", start)
        return json.loads(content[start:end])

    def test_only_current_day_place_with_coordinates_included(self):
        place = WantToGo.objects.create(
            itinerary=self.itinerary, name="首里城", address="那覇市", latitude=26.2, longitude=127.7,
        )
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="観光", start_time=time(10, 0), place=place,
        )
        response = self.client.get(self.url)
        data = self._get_schedule_map_data(response)

        self.assertEqual(len(data["1"]), 1)
        self.assertEqual(data["1"][0]["id"], place.id)
        self.assertEqual(data["1"][0]["name"], "首里城")
        self.assertEqual(data["2"], [])
        self.assertEqual(data["3"], [])

    def test_day_index_wins_over_want_to_go_planned_day(self):
        place = WantToGo.objects.create(
            itinerary=self.itinerary, name="美ら海水族館", latitude=26.7, longitude=127.9, planned_day=1,
        )
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 2), day_index=2,
            title="観光", start_time=time(9, 0), place=place,
        )
        response = self.client.get(self.url)
        data = self._get_schedule_map_data(response)

        self.assertEqual(data["1"], [])
        self.assertEqual([p["id"] for p in data["2"]], [place.id])

    def test_same_place_same_day_deduplicated(self):
        place = WantToGo.objects.create(itinerary=self.itinerary, name="A", latitude=1.0, longitude=1.0)
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="午前", start_time=time(9, 0), place=place,
        )
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="午後", start_time=time(15, 0), place=place,
        )
        response = self.client.get(self.url)
        data = self._get_schedule_map_data(response)
        self.assertEqual(len(data["1"]), 1)

    def test_same_place_different_day_included_in_both(self):
        place = WantToGo.objects.create(itinerary=self.itinerary, name="A", latitude=1.0, longitude=1.0)
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="Day1", start_time=time(9, 0), place=place,
        )
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 2), day_index=2,
            title="Day2", start_time=time(9, 0), place=place,
        )
        response = self.client.get(self.url)
        data = self._get_schedule_map_data(response)
        self.assertEqual([p["id"] for p in data["1"]], [place.id])
        self.assertEqual([p["id"] for p in data["2"]], [place.id])

    def test_schedule_without_place_excluded(self):
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="移動", start_time=time(9, 0), place=None,
        )
        response = self.client.get(self.url)
        data = self._get_schedule_map_data(response)
        self.assertEqual(data["1"], [])

    def test_place_without_coordinates_excluded(self):
        place = WantToGo.objects.create(itinerary=self.itinerary, name="住所のみ", address="どこか")
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="観光", start_time=time(9, 0), place=place,
        )
        response = self.client.get(self.url)
        data = self._get_schedule_map_data(response)
        self.assertEqual(data["1"], [])

    def test_out_of_range_coordinates_excluded(self):
        place = WantToGo.objects.create(itinerary=self.itinerary, name="不正座標", latitude=91.0, longitude=200.0)
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="観光", start_time=time(9, 0), place=place,
        )
        response = self.client.get(self.url)
        data = self._get_schedule_map_data(response)
        self.assertEqual(data["1"], [])

    def test_place_from_other_itinerary_excluded(self):
        other_itinerary = Itinerary.objects.create(
            title="Other Trip", start_date=date(2026, 2, 1), end_date=date(2026, 2, 3),
        )
        other_place = WantToGo.objects.create(
            itinerary=other_itinerary, name="別のしおりの場所", latitude=1.0, longitude=1.0,
        )
        # データ不整合を模した状況(通常のUIでは起こらない)でも安全側に倒れることを確認する。
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="観光", start_time=time(9, 0), place=other_place,
        )
        response = self.client.get(self.url)
        data = self._get_schedule_map_data(response)
        self.assertEqual(data["1"], [])

    def test_query_count_does_not_scale_with_schedule_count(self):
        place = WantToGo.objects.create(itinerary=self.itinerary, name="A", latitude=1.0, longitude=1.0)
        for i in range(5):
            ScheduleV2.objects.create(
                itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
                title=f"予定{i}", start_time=time(9, i), place=place, order=i,
            )

        # QRコード生成はしおりごとに初回のみ書き込みが走るため、計測前に一度呼んでおく。
        self.client.get(self.url)

        with CaptureQueriesContext(connection) as baseline:
            self.client.get(self.url)

        for i in range(5, 25):
            ScheduleV2.objects.create(
                itinerary=self.itinerary, date=date(2026, 1, 2), day_index=2,
                title=f"予定{i}", start_time=time(9, i % 60), place=place, order=i,
            )

        with CaptureQueriesContext(connection) as more_schedules:
            self.client.get(self.url)

        self.assertEqual(len(baseline.captured_queries), len(more_schedules.captured_queries))

    def test_map_display_config_and_data_script_present(self):
        response = self.client.get(self.url)
        content = response.content.decode("utf-8")
        self.assertIn('id="tabisync-map-config"', content)
        self.assertIn('id="schedule-map-data"', content)


class EditMenuV2ViewTests(TestCase):
    def test_get_returns_200_without_edit_password(self):
        itinerary = Itinerary.objects.create(title="Test Trip")
        url = reverse("tabisync:content_edit_v2", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
