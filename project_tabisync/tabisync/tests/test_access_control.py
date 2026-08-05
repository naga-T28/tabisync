import json
import shutil
import tempfile
from datetime import date

from django.contrib.auth.hashers import make_password
from django.core import signing
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from ..models import ChecklistV2, Itinerary, MemoV2, ScheduleV2, WantToGo
from ..views.access_control import (
    build_edit_session_key,
    build_view_session_key,
    grant_edit_access,
    grant_view_access,
    handle_edit_password_gate,
    has_edit_access,
    has_view_access,
    require_edit_access_json,
    require_view_access,
    require_view_access_json,
)


def _make_itinerary(**kwargs):
    defaults = {
        "title": "Test Trip",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 3),
    }
    defaults.update(kwargs)
    return Itinerary.objects.create(**defaults)


class SessionKeyGenerationTests(TestCase):
    def test_view_session_key_stable_for_same_password(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="secret", edit_pw="")
        itinerary.save()

        self.assertEqual(build_view_session_key(itinerary), build_view_session_key(itinerary))

    def test_view_session_key_changes_when_password_reset(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="secret", edit_pw="")
        itinerary.save()
        old_key = build_view_session_key(itinerary)

        itinerary.set_passwords(view_pw="new-secret", edit_pw="")
        itinerary.save()
        new_key = build_view_session_key(itinerary)

        self.assertNotEqual(old_key, new_key)

    def test_edit_session_key_changes_when_password_reset(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="", edit_pw="secret")
        itinerary.save()
        old_key = build_edit_session_key(itinerary)

        itinerary.set_passwords(view_pw="", edit_pw="new-secret")
        itinerary.save()
        new_key = build_edit_session_key(itinerary)

        self.assertNotEqual(old_key, new_key)

    def test_resetting_view_password_does_not_change_edit_key(self):
        # ResetPasswordView等の実際のリセット処理はview_password/edit_passwordの
        # 片方だけを直接書き換える（set_passwordsのように両方を再ハッシュしない）ため、
        # そのパターンを再現する。
        itinerary = _make_itinerary()
        itinerary.view_password = make_password("v1")
        itinerary.edit_password = make_password("e1")
        itinerary.save()
        old_edit_key = build_edit_session_key(itinerary)

        itinerary.view_password = make_password("v2")
        itinerary.save()

        self.assertEqual(old_edit_key, build_edit_session_key(itinerary))

    def test_no_password_produces_stable_key(self):
        itinerary = _make_itinerary()
        self.assertEqual(build_view_session_key(itinerary), build_view_session_key(itinerary))
        self.assertIn("none", build_view_session_key(itinerary))


class HasAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request_with_session(self):
        request = self.factory.get("/")
        request.session = self.client.session
        return request

    def test_has_view_access_true_when_no_password(self):
        itinerary = _make_itinerary()
        request = self._request_with_session()
        self.assertTrue(has_view_access(request, itinerary))

    def test_has_view_access_false_until_granted(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="secret", edit_pw="")
        itinerary.save()
        request = self._request_with_session()

        self.assertFalse(has_view_access(request, itinerary))
        grant_view_access(request, itinerary)
        request.session.save()

        request2 = self.factory.get("/")
        request2.session = request.session
        self.assertTrue(has_view_access(request2, itinerary))

    def test_has_edit_access_false_until_granted(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="", edit_pw="secret")
        itinerary.save()
        request = self._request_with_session()

        self.assertFalse(has_edit_access(request, itinerary))
        grant_edit_access(request, itinerary)
        self.assertTrue(has_edit_access(request, itinerary))


class RequireViewAccessResponseShapeTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.itinerary = _make_itinerary()
        self.itinerary.set_passwords(view_pw="secret", edit_pw="")
        self.itinerary.save()

    def test_html_request_redirects_to_password_page(self):
        request = self.factory.get("/")
        request.session = self.client.session
        response = require_view_access(request, self.itinerary)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.itinerary.token), response.url)

    def test_json_request_returns_403(self):
        request = self.factory.get("/")
        request.META["CONTENT_TYPE"] = "application/json"
        request.session = self.client.session
        response = require_view_access(request, self.itinerary)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 403)

    def test_returns_none_when_authorized(self):
        request = self.factory.get("/")
        request.session = self.client.session
        grant_view_access(request, self.itinerary)
        self.assertIsNone(require_view_access(request, self.itinerary))

    def test_require_view_access_json_always_returns_403_regardless_of_content_type(self):
        request = self.factory.get("/")
        request.session = self.client.session
        response = require_view_access_json(request, self.itinerary)
        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertEqual(payload["status"], "error")


class RequireEditAccessJsonTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.itinerary = _make_itinerary()
        self.itinerary.set_passwords(view_pw="", edit_pw="secret")
        self.itinerary.save()

    def test_returns_403_when_not_authorized(self):
        request = self.factory.get("/")
        request.session = self.client.session
        response = require_edit_access_json(request, self.itinerary)
        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertEqual(payload["status"], "error")

    def test_returns_none_when_authorized(self):
        request = self.factory.get("/")
        request.session = self.client.session
        grant_edit_access(request, self.itinerary)
        self.assertIsNone(require_edit_access_json(request, self.itinerary))


class HandleEditPasswordGateTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.itinerary = _make_itinerary()
        self.itinerary.set_passwords(view_pw="", edit_pw="edit-secret")
        self.itinerary.save()

    def test_get_unauthorized_renders_password_form(self):
        request = self.factory.get("/")
        request.session = self.client.session
        response = handle_edit_password_gate(request, self.itinerary, "content_edit_v2")
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)

    def test_json_post_unauthorized_returns_403(self):
        request = self.factory.post("/", data=json.dumps({}), content_type="application/json")
        request.session = self.client.session
        response = handle_edit_password_gate(request, self.itinerary, "content_edit_v2")
        self.assertEqual(response.status_code, 403)

    def test_form_post_with_correct_password_grants_access_and_redirects(self):
        request = self.factory.post("/", {"password": "edit-secret"})
        request.session = self.client.session
        response = handle_edit_password_gate(request, self.itinerary, "content_edit_v2")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(request.session.get(build_edit_session_key(self.itinerary)))

    def test_form_post_with_wrong_password_returns_error_form(self):
        request = self.factory.post("/", {"password": "wrong"})
        request.session = self.client.session
        response = handle_edit_password_gate(request, self.itinerary, "content_edit_v2")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(request.session.get(build_edit_session_key(self.itinerary)))

    def test_returns_none_when_already_authorized(self):
        request = self.factory.get("/")
        request.session = self.client.session
        grant_edit_access(request, self.itinerary)
        self.assertIsNone(handle_edit_password_gate(request, self.itinerary, "content_edit_v2"))


# ============================================================
# 権限表パラメータテスト: 全V2閲覧URL・編集URL・更新APIについて
# パスワードなし／閲覧のみ／編集済みの組み合わせを検証する。
# ============================================================

VIEW_GATED_URL_NAMES = [
    "content",       # V1
    "content_memo",  # V1
    "content_list",  # V1
    "content_v2",    # V2
    "Wantto",
    "V2_memo",
    "V2_list",
    "V2_concierge",
]

EDIT_GATED_URL_NAMES = [
    "edit",                  # V1
    "content_edit_v2",
    "content_edit_form_v2",
    "Scheduleedit",
    "Wantedit",
    "V2_memo_edit",
    "V2_list_edit",
]


_MEDIA_ROOT = tempfile.mkdtemp(prefix="tabisync-test-access-control-media-")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ViewGatedPagePermissionMatrixTests(TestCase):
    # content_v2 (ItineraryDetailV2View) はGETのたびにQRコード画像を実ファイルとして
    # 保存するため、実プロジェクトのmedia/を汚さないよう隔離したMEDIA_ROOTを使う。
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def _url(self, name, itinerary):
        return reverse(f"tabisync:{name}", kwargs={"pk": itinerary.pk, "token": itinerary.token})

    def test_no_password_allows_direct_access(self):
        itinerary = _make_itinerary()
        for name in VIEW_GATED_URL_NAMES:
            with self.subTest(url_name=name):
                response = self.client.get(self._url(name, itinerary))
                self.assertEqual(response.status_code, 200, name)

    def test_view_password_without_session_redirects(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="secret", edit_pw="")
        itinerary.save()
        for name in VIEW_GATED_URL_NAMES:
            with self.subTest(url_name=name):
                response = self.client.get(self._url(name, itinerary))
                self.assertEqual(response.status_code, 302, name)
                self.assertIn("password", response.url)

    def test_view_password_with_session_allows_access(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="secret", edit_pw="")
        itinerary.save()
        session = self.client.session
        session[build_view_session_key(itinerary)] = True
        session.save()

        for name in VIEW_GATED_URL_NAMES:
            with self.subTest(url_name=name):
                response = self.client.get(self._url(name, itinerary))
                self.assertEqual(response.status_code, 200, name)


class EditGatedPagePermissionMatrixTests(TestCase):
    def _url(self, name, itinerary):
        return reverse(f"tabisync:{name}", kwargs={"pk": itinerary.pk, "token": itinerary.token})

    def test_no_edit_password_allows_direct_access(self):
        itinerary = _make_itinerary()
        for name in EDIT_GATED_URL_NAMES:
            with self.subTest(url_name=name):
                response = self.client.get(self._url(name, itinerary))
                self.assertEqual(response.status_code, 200, name)

    def test_edit_password_without_session_shows_password_form(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="", edit_pw="secret")
        itinerary.save()
        for name in EDIT_GATED_URL_NAMES:
            with self.subTest(url_name=name):
                response = self.client.get(self._url(name, itinerary))
                self.assertEqual(response.status_code, 200, name)
                self.assertTemplateUsed(response, "tabisync/edit_password.html")

    def test_edit_password_with_session_allows_real_content(self):
        itinerary = _make_itinerary()
        itinerary.set_passwords(view_pw="", edit_pw="secret")
        itinerary.save()
        session = self.client.session
        session[build_edit_session_key(itinerary)] = True
        session.save()

        for name in EDIT_GATED_URL_NAMES:
            with self.subTest(url_name=name):
                response = self.client.get(self._url(name, itinerary))
                self.assertEqual(response.status_code, 200, name)
                self.assertTemplateNotUsed(response, "tabisync/edit_password.html")


class UpdateApiEditGateTests(TestCase):
    """編集ゲート付きの更新API群。未認証は一貫して403(JSON)、認証済みは通常応答になる。"""

    def setUp(self):
        self.itinerary = _make_itinerary()
        self.itinerary.set_passwords(view_pw="", edit_pw="secret")
        self.itinerary.save()

    def _post(self, url_name, payload):
        url = reverse(f"tabisync:{url_name}", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def _grant_edit_session(self):
        session = self.client.session
        session[build_edit_session_key(self.itinerary)] = True
        session.save()

    def test_all_update_endpoints_reject_unauthenticated_json_post(self):
        cases = [
            ("schedule_v2_row_save", {}),
            ("schedule_v2_row_delete", {"id": 1}),
            ("Wantedit", {"action": "save_want_to_go", "name": "x"}),
            ("V2_memo", {"notes": []}),
            ("V2_memo_edit", {"notes": []}),
            ("V2_list", {"lists": []}),
            ("V2_list_edit", {"lists": []}),
            ("V2_concierge_apply", {"edit_actions": []}),
        ]
        for url_name, payload in cases:
            with self.subTest(url_name=url_name):
                response = self._post(url_name, payload)
                self.assertEqual(response.status_code, 403, url_name)
                data = json.loads(response.content.decode("utf-8"))
                self.assertEqual(data["status"], "error")

    def test_authenticated_schedule_row_save_succeeds(self):
        self._grant_edit_session()
        response = self._post("schedule_v2_row_save", {
            "title": "予定", "start_time": "09:00", "date": "day-1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ScheduleV2.objects.filter(itinerary=self.itinerary).count(), 1)

    def test_authenticated_want_to_go_save_succeeds(self):
        self._grant_edit_session()
        response = self._post("Wantedit", {"action": "save_want_to_go", "name": "スポット"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 1)

    def test_authenticated_memo_save_succeeds(self):
        self._grant_edit_session()
        response = self._post("V2_memo_edit", {"notes": [{"content": "メモ"}]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("メモ", MemoV2.objects.get(itinerary=self.itinerary).content)

    def test_authenticated_checklist_save_succeeds(self):
        self._grant_edit_session()
        response = self._post("V2_list_edit", {"lists": [{"id": "l1", "title": "リスト", "items": []}]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("リスト", ChecklistV2.objects.get(itinerary=self.itinerary).content)


class PasswordResetInvalidatesOldSessionTests(TestCase):
    """パスワード再設定後、旧編集セッションでは変更できなくなることを回帰的に確認する。"""

    def setUp(self):
        self.itinerary = _make_itinerary()
        self.itinerary.set_passwords(view_pw="", edit_pw="old-secret")
        self.itinerary.save()

        session = self.client.session
        session[build_edit_session_key(self.itinerary)] = True
        session.save()

    def test_old_edit_session_rejected_after_password_reset_via_view(self):
        # 事前: 旧セッションで編集APIが使えることを確認
        url = reverse("tabisync:schedule_v2_row_save", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        ok_response = self.client.post(
            url,
            data=json.dumps({"title": "予定A", "start_time": "09:00", "date": "day-1"}),
            content_type="application/json",
        )
        self.assertEqual(ok_response.status_code, 200)

        # パスワード再設定（ItineraryPasswordViewと同様、reset-linkフロー経由でedit_passwordを変更）
        signed_token = signing.dumps(
            {"pk": self.itinerary.pk, "token": str(self.itinerary.token), "type": "edit"},
            salt="tabisync-password-reset",
        )
        reset_url = reverse("tabisync:reset_password", kwargs={"signed_token": signed_token})
        reset_response = self.client.post(reset_url, {"password": "new-secret"})
        self.assertEqual(reset_response.status_code, 302)

        # 事後: 同じブラウザセッション(旧edit_authキー)のままでは編集APIも編集ページも拒否される
        response = self.client.post(
            url,
            data=json.dumps({"title": "予定B", "start_time": "10:00", "date": "day-1"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ScheduleV2.objects.filter(itinerary=self.itinerary).count(), 1)

        edit_page_url = reverse("tabisync:content_edit_v2", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        edit_page_response = self.client.get(edit_page_url)
        self.assertTemplateUsed(edit_page_response, "tabisync/edit_password.html")

    def test_new_password_grants_fresh_access(self):
        self.itinerary.set_passwords(view_pw="", edit_pw="new-secret")
        self.itinerary.save()

        url = reverse("tabisync:content_edit_v2", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        auth_response = self.client.post(url, {"password": "new-secret"})
        self.assertEqual(auth_response.status_code, 302)
        self.assertTrue(self.client.session.get(build_edit_session_key(self.itinerary)))
