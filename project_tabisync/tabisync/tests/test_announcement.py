from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ..models import Itinerary, SiteAnnouncement


class AnnouncementContextProcessorTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(title="テスト旅行")
        self.other_itinerary = Itinerary.objects.create(title="別の旅行")
        self.home_url = reverse("tabisync:home")
        self.itinerary_url = reverse(
            "tabisync:content_v2", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token}
        )
        self.other_itinerary_url = reverse(
            "tabisync:content_v2",
            kwargs={"pk": self.other_itinerary.pk, "token": self.other_itinerary.token},
        )

    def test_inactive_announcement_is_not_shown(self):
        SiteAnnouncement.objects.create(
            title="無効化されたお知らせ", message="表示されないはず", is_active=False, show_on_home=True,
        )
        response = self.client.get(self.home_url)
        self.assertIsNone(response.context["active_announcement"])

    def test_future_start_is_not_shown(self):
        SiteAnnouncement.objects.create(
            title="未来のお知らせ", message="まだ表示されない", is_active=True, show_on_home=True,
            starts_at=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(self.home_url)
        self.assertIsNone(response.context["active_announcement"])

    def test_past_end_is_not_shown(self):
        SiteAnnouncement.objects.create(
            title="終了したお知らせ", message="もう表示されない", is_active=True, show_on_home=True,
            ends_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.get(self.home_url)
        self.assertIsNone(response.context["active_announcement"])

    def test_show_on_home_appears_on_home_only(self):
        SiteAnnouncement.objects.create(
            title="ホーム向け", message="ホームのお知らせ", is_active=True, show_on_home=True,
        )
        home_response = self.client.get(self.home_url)
        itinerary_response = self.client.get(self.itinerary_url)

        self.assertIsNotNone(home_response.context["active_announcement"])
        self.assertIsNone(itinerary_response.context["active_announcement"])

    def test_show_on_all_itineraries_appears_on_any_itinerary(self):
        SiteAnnouncement.objects.create(
            title="全しおり向け", message="メンテナンスのお知らせ", is_active=True,
            show_on_all_itineraries=True,
        )
        response = self.client.get(self.itinerary_url)
        other_response = self.client.get(self.other_itinerary_url)

        self.assertIsNotNone(response.context["active_announcement"])
        self.assertIsNotNone(other_response.context["active_announcement"])

    def test_specific_itinerary_targeting_is_scoped(self):
        announcement = SiteAnnouncement.objects.create(
            title="個別指定", message="このしおりだけ", is_active=True,
            show_on_all_itineraries=False,
        )
        announcement.itineraries.add(self.itinerary)

        targeted_response = self.client.get(self.itinerary_url)
        other_response = self.client.get(self.other_itinerary_url)

        self.assertIsNotNone(targeted_response.context["active_announcement"])
        self.assertIsNone(other_response.context["active_announcement"])

    def test_multiple_qualifying_announcements_show_only_the_latest(self):
        SiteAnnouncement.objects.create(
            title="古いお知らせ", message="古い", is_active=True, show_on_home=True,
        )
        newest = SiteAnnouncement.objects.create(
            title="新しいお知らせ", message="新しい", is_active=True, show_on_home=True,
        )
        response = self.client.get(self.home_url)
        self.assertEqual(response.context["active_announcement"].id, newest.id)

    def test_non_target_pages_never_receive_an_announcement(self):
        SiteAnnouncement.objects.create(
            title="全部に出したいお知らせ", message="出ないはず", is_active=True,
            show_on_home=True, show_on_all_itineraries=True,
        )
        response = self.client.get(reverse("tabisync:qa"))
        self.assertIsNone(response.context["active_announcement"])
        self.assertNotContains(response, "announcement-banner")

    def test_message_is_escaped_in_rendered_html(self):
        SiteAnnouncement.objects.create(
            title="XSSテスト", message="<script>alert(1)</script>", is_active=True, show_on_home=True,
        )
        response = self.client.get(self.home_url)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_banner_renders_on_itinerary_page(self):
        SiteAnnouncement.objects.create(
            title="しおりページ表示確認", message="メンテナンス予定のお知らせ", is_active=True,
            show_on_all_itineraries=True,
        )
        response = self.client.get(self.itinerary_url)
        self.assertContains(response, "announcement-banner")
        self.assertContains(response, "メンテナンス予定のお知らせ")

    def test_home_banner_renders_below_hero_with_x_link(self):
        SiteAnnouncement.objects.create(
            title="ホーム表示確認", message="メンテナンスのお知らせ", is_active=True, show_on_home=True,
        )
        response = self.client.get(self.home_url)
        content = response.content.decode()

        self.assertContains(response, "home-announcement-section")
        self.assertContains(response, "メンテナンスのお知らせ")
        self.assertContains(response, 'href="https://x.com/tabisync_com"')
        self.assertContains(response, "公式X（@tabisync_com）")

        # MV(.home-hero)の閉じタグより後、次セクション(.home-recent-section)より前にあることを確認する。
        hero_end = content.index("</section>")
        announcement_index = content.index("home-announcement-section")
        next_section_index = content.index("home-recent-section")
        self.assertLess(hero_end, announcement_index)
        self.assertLess(announcement_index, next_section_index)
