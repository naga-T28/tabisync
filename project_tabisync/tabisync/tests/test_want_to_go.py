import json
import threading
from datetime import date

from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from ..models import Itinerary, WantToGo
from ..views.access_control import build_edit_session_key, build_view_session_key


def _make_itinerary(**kwargs):
    defaults = {
        "title": "Test Trip",
        "want_to_go_limit": 2,
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 3),
    }
    defaults.update(kwargs)
    return Itinerary.objects.create(**defaults)


class WantToGoV2ViewNoPasswordTests(TestCase):
    """パスワードなしのしおりでは、これまで通り編集APIが即座に利用できる（現行仕様の固定）。"""

    def setUp(self):
        self.itinerary = _make_itinerary()
        self.url = reverse(
            "tabisync:Wantedit",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_save_want_to_go_creates_place(self):
        payload = {"action": "save_want_to_go", "name": "首里城", "address": "那覇市"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "saved")
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 1)

    def test_save_want_to_go_rejects_over_limit(self):
        self.itinerary.want_to_go_list.create(name="スポット1")
        self.itinerary.want_to_go_list.create(name="スポット2")

        payload = {"action": "save_want_to_go", "name": "スポット3"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 2)

    def test_delete_want_to_go_removes_place(self):
        place = self.itinerary.want_to_go_list.create(name="削除対象")
        payload = {"action": "delete_want_to_go", "id": place.id}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(data["status"], "deleted")
        self.assertFalse(WantToGo.objects.filter(pk=place.pk).exists())

    def test_invalid_json_returns_400(self):
        response = self.client.post(self.url, data="not-json", content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")

    def test_unknown_action_returns_400(self):
        response = self.client.post(
            self.url, data=json.dumps({"action": "delete_everything"}), content_type="application/json"
        )
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")

    def test_update_without_id_returns_400(self):
        response = self.client.post(
            self.url, data=json.dumps({"action": "update_want_to_go"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_nonexistent_id_returns_404(self):
        response = self.client.post(
            self.url, data=json.dumps({"action": "delete_want_to_go", "id": 999999}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)


class WantToGoV2ViewEditAuthorizationTests(TestCase):
    """編集パスワードが設定されている場合の認可挙動。"""

    def setUp(self):
        self.itinerary = _make_itinerary()
        self.itinerary.set_passwords(view_pw="", edit_pw="edit-secret")
        self.itinerary.save()
        self.url = reverse(
            "tabisync:Wantedit",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def _post_json(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_get_without_edit_auth_shows_password_form_not_edit_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tabisync/edit_password.html")

    def test_create_without_edit_auth_returns_403_and_no_db_change(self):
        response = self._post_json({"action": "save_want_to_go", "name": "無断作成"})
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(data["status"], "error")
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 0)

    def test_update_without_edit_auth_returns_403_and_no_db_change(self):
        place = self.itinerary.want_to_go_list.create(name="既存スポット")
        response = self._post_json({"action": "update_want_to_go", "id": place.id, "name": "改ざん"})
        data = json.loads(response.content.decode("utf-8"))
        place.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(data["status"], "error")
        self.assertEqual(place.name, "既存スポット")

    def test_delete_without_edit_auth_returns_403_and_no_db_change(self):
        place = self.itinerary.want_to_go_list.create(name="消されたくないスポット")
        response = self._post_json({"action": "delete_want_to_go", "id": place.id})
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(data["status"], "error")
        self.assertTrue(WantToGo.objects.filter(pk=place.pk).exists())

    def test_view_auth_alone_does_not_grant_edit_access(self):
        # view_password は設定していないが、閲覧セッションだけを持たせても編集は不可。
        session = self.client.session
        session[build_view_session_key(self.itinerary)] = True
        session.save()

        response = self._post_json({"action": "save_want_to_go", "name": "閲覧権限だけで作成"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 0)

    def test_edit_authentication_via_password_form_allows_subsequent_mutations(self):
        auth_response = self.client.post(self.url, {"password": "edit-secret"})
        self.assertEqual(auth_response.status_code, 302)
        self.assertTrue(self.client.session.get(build_edit_session_key(self.itinerary)))

        response = self._post_json({"action": "save_want_to_go", "name": "認証後に作成"})
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "saved")
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 1)

    def test_wrong_password_does_not_grant_access(self):
        response = self.client.post(self.url, {"password": "wrong-password"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tabisync/edit_password.html")
        self.assertFalse(self.client.session.get(build_edit_session_key(self.itinerary)))


class WantToGoCrossItineraryTests(TestCase):
    def test_cannot_update_place_belonging_to_another_itinerary(self):
        itinerary_a = _make_itinerary(title="A")
        itinerary_b = _make_itinerary(title="B")
        place_in_b = itinerary_b.want_to_go_list.create(name="別しおりのスポット")

        url = reverse("tabisync:Wantedit", kwargs={"pk": itinerary_a.pk, "token": itinerary_a.token})
        response = self.client.post(
            url,
            data=json.dumps({"action": "update_want_to_go", "id": place_in_b.id, "name": "乗っ取り"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        place_in_b.refresh_from_db()
        self.assertEqual(place_in_b.name, "別しおりのスポット")

    def test_cannot_delete_place_belonging_to_another_itinerary(self):
        itinerary_a = _make_itinerary(title="A")
        itinerary_b = _make_itinerary(title="B")
        place_in_b = itinerary_b.want_to_go_list.create(name="別しおりのスポット")

        url = reverse("tabisync:Wantedit", kwargs={"pk": itinerary_a.pk, "token": itinerary_a.token})
        response = self.client.post(
            url,
            data=json.dumps({"action": "delete_want_to_go", "id": place_in_b.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(WantToGo.objects.filter(pk=place_in_b.pk).exists())


class WantToGoMapViewTests(TestCase):
    """閲覧専用ページ。変更操作は一切受け付けない。"""

    def setUp(self):
        self.itinerary = _make_itinerary()
        self.url = reverse(
            "tabisync:Wantto",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_is_not_allowed(self):
        payload = {"action": "save_want_to_go", "name": "閲覧ページ経由の作成"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 0)


class WantToGoConcurrentCreationTests(TransactionTestCase):
    """複数リクエストが同時に件数上限へ書き込もうとしても、上限を超えないことを検証する。

    テストDB(SQLite)は行ロック(select_for_update)を実質サポートしないため、
    このテストが保証するのは「最終的なDB状態が上限を超えない」という不変条件のみであり、
    本番のPostgreSQLで行われる真の直列化そのものを再現するものではない。
    """

    def test_concurrent_saves_do_not_exceed_limit(self):
        itinerary = _make_itinerary(want_to_go_limit=3)
        url = reverse("tabisync:Wantedit", kwargs={"pk": itinerary.pk, "token": itinerary.token})

        thread_count = 6
        barrier = threading.Barrier(thread_count)
        outcomes = []
        lock = threading.Lock()

        def worker(index):
            barrier.wait()
            client = Client()
            payload = {"action": "save_want_to_go", "name": f"スポット{index}"}
            try:
                response = client.post(url, data=json.dumps(payload), content_type="application/json")
                outcome = response.status_code
            except Exception:
                outcome = "error"
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_count = WantToGo.objects.filter(itinerary=itinerary).count()
        self.assertLessEqual(final_count, itinerary.want_to_go_limit, f"outcomes={outcomes}")
