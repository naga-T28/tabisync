from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings

from ..views.utils import (
    UNKNOWN_CLIENT_IP,
    build_public_service_error_message,
    count_memo_words,
    get_client_ip,
    get_inclusive_day_count,
    parse_json_object_body,
    ratelimit_client_ip,
    validate_checklist_limits,
    validate_memo_notes_limits,
    verify_turnstile,
)


class ClientIpUntrustedSourceTests(TestCase):
    """TRUSTED_PROXY_CIDRS未設定（既定・安全側）の場合、転送ヘッダーは一切信頼しない。"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_default_settings_ignore_cf_connecting_ip_spoofing(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="203.0.113.5",
            HTTP_CF_CONNECTING_IP="1.2.3.4",
        )
        self.assertEqual(get_client_ip(request), "203.0.113.5")

    def test_default_settings_ignore_x_forwarded_for_spoofing(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="203.0.113.5",
            HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8",
        )
        self.assertEqual(get_client_ip(request), "203.0.113.5")

    @override_settings(TRUSTED_PROXY_CIDRS=["192.168.1.1/32"])
    def test_headers_ignored_when_remote_addr_outside_trusted_cidr(self):
        # TRUSTED_PROXY_CIDRSが設定されていても、直前ホップ(REMOTE_ADDR)がその
        # 範囲外なら転送ヘッダーは信頼しない。
        request = self.factory.get(
            "/",
            REMOTE_ADDR="203.0.113.5",
            HTTP_CF_CONNECTING_IP="1.2.3.4",
        )
        self.assertEqual(get_client_ip(request), "203.0.113.5")


class ClientIpTrustedProxyTests(TestCase):
    """settings.TRUSTED_PROXY_CIDRS で明示的に信頼した直前ホップ経由の場合のみ転送ヘッダーを使う。"""

    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUSTED_PROXY_CIDRS=["10.0.0.1/32"])
    def test_prefers_cloudflare_header_over_x_forwarded_for(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.10, 10.0.0.1",
            HTTP_CF_CONNECTING_IP="203.0.113.10",
        )
        self.assertEqual(get_client_ip(request), "203.0.113.10")

    @override_settings(TRUSTED_PROXY_CIDRS=["10.0.0.1/32"])
    def test_falls_back_to_first_forwarded_ip_when_no_cf_header(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.10, 10.0.0.1",
        )
        self.assertEqual(get_client_ip(request), "198.51.100.10")

    @override_settings(TRUSTED_PROXY_CIDRS=["10.0.0.1/32"])
    def test_ignores_invalid_headers_and_uses_next_valid_xff_entry(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="unknown, 198.51.100.20",
            HTTP_CF_CONNECTING_IP="not-an-ip",
        )
        self.assertEqual(get_client_ip(request), "198.51.100.20")

    @override_settings(TRUSTED_PROXY_CIDRS=["10.0.0.0/8"])
    def test_cidr_range_matches_any_address_within_it(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.5.5.5",
            HTTP_CF_CONNECTING_IP="203.0.113.99",
        )
        self.assertEqual(get_client_ip(request), "203.0.113.99")

    @override_settings(TRUSTED_PROXY_CIDRS=["2001:db8::/32"])
    def test_trusted_ipv6_proxy_forwards_cf_header(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="2001:db8::1",
            HTTP_CF_CONNECTING_IP="2001:db8:1::42",
        )
        self.assertEqual(get_client_ip(request), "2001:db8:1::42")

    @override_settings(TRUSTED_PROXY_CIDRS=["not-a-valid-cidr", "10.0.0.1/32"])
    def test_invalid_cidr_entries_are_skipped_without_error(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_CF_CONNECTING_IP="203.0.113.10",
        )
        self.assertEqual(get_client_ip(request), "203.0.113.10")


class ClientIpEdgeCaseTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_ipv4_remote_addr_used_directly_without_trust_config(self):
        request = self.factory.get("/", REMOTE_ADDR="198.51.100.10")
        self.assertEqual(get_client_ip(request), "198.51.100.10")

    def test_ipv6_remote_addr_used_directly_without_trust_config(self):
        request = self.factory.get("/", REMOTE_ADDR="2001:db8::5")
        self.assertEqual(get_client_ip(request), "2001:db8::5")

    def test_invalid_remote_addr_returns_unknown_sentinel(self):
        request = self.factory.get("/", REMOTE_ADDR="not-an-ip")
        self.assertEqual(get_client_ip(request), UNKNOWN_CLIENT_IP)

    def test_empty_remote_addr_returns_unknown_sentinel_not_empty_string(self):
        request = self.factory.get("/", REMOTE_ADDR="")
        result = get_client_ip(request)
        self.assertEqual(result, UNKNOWN_CLIENT_IP)
        self.assertNotEqual(result, "")

    def test_ratelimit_client_ip_uses_same_resolution(self):
        request = self.factory.get("/", REMOTE_ADDR="198.51.100.10")
        self.assertEqual(ratelimit_client_ip(None, request), "198.51.100.10")


@patch.dict("os.environ", {"CLOUDFLARE_TURNSTILE_SECRET_KEY": "test-secret"})
class VerifyTurnstileTests(TestCase):
    """verify_turnstileがjson.loadsを使うため、json未importの回帰を防ぐ。

    CLOUDFLARE_TURNSTILE_SECRET_KEYはこのクラス全体でモックし、
    実行環境の.env設定に依存しないようにする。
    """

    def setUp(self):
        self.factory = RequestFactory()

    @patch("tabisync.views.utils.urllib.request.urlopen")
    def test_returns_true_on_successful_verification(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        request = self.factory.post("/", {"cf-turnstile-response": "token"})
        self.assertTrue(verify_turnstile(request))

    @patch("tabisync.views.utils.urllib.request.urlopen")
    def test_returns_false_on_unsuccessful_verification(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": false}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        request = self.factory.post("/", {"cf-turnstile-response": "token"})
        self.assertFalse(verify_turnstile(request))

    def test_returns_false_without_token(self):
        request = self.factory.post("/", {})
        self.assertFalse(verify_turnstile(request))

    @patch.dict("os.environ", {"CLOUDFLARE_TURNSTILE_SECRET_KEY": ""})
    @patch("tabisync.views.utils.urllib.request.urlopen")
    def test_returns_false_and_skips_network_call_when_secret_not_configured(self, mock_urlopen):
        request = self.factory.post("/", {"cf-turnstile-response": "token"})
        self.assertFalse(verify_turnstile(request))
        mock_urlopen.assert_not_called()

    @patch("tabisync.views.utils.urllib.request.urlopen")
    def test_returns_false_on_timeout(self, mock_urlopen):
        import socket

        mock_urlopen.side_effect = socket.timeout("timed out")

        request = self.factory.post("/", {"cf-turnstile-response": "token"})
        self.assertFalse(verify_turnstile(request))

    @patch("tabisync.views.utils.urllib.request.urlopen")
    def test_uses_configured_timeout(self, mock_urlopen):
        from ..views.utils import TURNSTILE_TIMEOUT_SECONDS

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        request = self.factory.post("/", {"cf-turnstile-response": "token"})
        verify_turnstile(request)

        self.assertEqual(mock_urlopen.call_args.kwargs.get("timeout"), TURNSTILE_TIMEOUT_SECONDS)

    @patch("tabisync.views.utils.urllib.request.urlopen")
    def test_returns_false_on_malformed_response_body(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not-json"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        request = self.factory.post("/", {"cf-turnstile-response": "token"})
        self.assertFalse(verify_turnstile(request))

    @patch("tabisync.views.utils.urllib.request.urlopen")
    def test_sends_resolved_client_ip_as_remoteip(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        request = self.factory.post(
            "/",
            {"cf-turnstile-response": "token"},
            REMOTE_ADDR="203.0.113.9",
        )
        verify_turnstile(request)

        sent_request = mock_urlopen.call_args.args[0]
        self.assertIn(b"203.0.113.9", sent_request.data)


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


class InclusiveDayCountTests(TestCase):
    def test_counts_both_endpoints(self):
        from datetime import date

        self.assertEqual(get_inclusive_day_count(date(2026, 1, 1), date(2026, 1, 1)), 1)
        self.assertEqual(get_inclusive_day_count(date(2026, 1, 1), date(2026, 1, 3)), 3)


class CountMemoWordsTests(TestCase):
    def test_counts_english_and_japanese_tokens(self):
        self.assertEqual(count_memo_words("hello world"), 2)
        self.assertEqual(count_memo_words("こんにちは"), 5)
        self.assertEqual(count_memo_words(""), 0)


class ValidateMemoNotesLimitsTests(TestCase):
    def test_rejects_too_many_notes(self):
        notes = [{"content": "x"} for _ in range(16)]
        error = validate_memo_notes_limits(notes)
        self.assertIsNotNone(error)
        self.assertIn("15件", error)

    def test_rejects_note_over_word_limit(self):
        notes = [{"content": "word " * 1001}]
        error = validate_memo_notes_limits(notes)
        self.assertIsNotNone(error)
        self.assertIn("1000語", error)

    def test_allows_notes_within_limits(self):
        notes = [{"content": "短いメモ"}]
        self.assertIsNone(validate_memo_notes_limits(notes))


class ValidateChecklistLimitsTests(TestCase):
    def test_rejects_too_many_lists(self):
        lists = [{"title": f"list-{i}", "items": []} for i in range(11)]
        error = validate_checklist_limits(lists)
        self.assertIsNotNone(error)
        self.assertIn("10リスト", error)

    def test_rejects_too_many_items_in_a_list(self):
        lists = [{"title": "持ち物", "items": [{"text": str(i)} for i in range(31)]}]
        error = validate_checklist_limits(lists)
        self.assertIsNotNone(error)
        self.assertIn("30個", error)

    def test_allows_lists_within_limits(self):
        lists = [{"title": "持ち物", "items": [{"text": "充電器"}]}]
        self.assertIsNone(validate_checklist_limits(lists))


class ParseJsonObjectBodyTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_valid_object_body_returns_data_and_no_error(self):
        request = self.factory.post("/", data='{"a": 1}', content_type="application/json")
        data, error_response = parse_json_object_body(request)
        self.assertEqual(data, {"a": 1})
        self.assertIsNone(error_response)

    def test_wrong_content_type_returns_400(self):
        request = self.factory.post("/", data='{"a": 1}', content_type="text/plain")
        data, error_response = parse_json_object_body(request)
        self.assertIsNone(data)
        self.assertEqual(error_response.status_code, 400)

    def test_empty_body_returns_400(self):
        request = self.factory.post("/", data="", content_type="application/json")
        data, error_response = parse_json_object_body(request)
        self.assertIsNone(data)
        self.assertEqual(error_response.status_code, 400)

    def test_array_top_level_returns_400(self):
        request = self.factory.post("/", data="[1, 2, 3]", content_type="application/json")
        data, error_response = parse_json_object_body(request)
        self.assertIsNone(data)
        self.assertEqual(error_response.status_code, 400)

    def test_scalar_top_level_returns_400(self):
        request = self.factory.post("/", data='"just a string"', content_type="application/json")
        data, error_response = parse_json_object_body(request)
        self.assertIsNone(data)
        self.assertEqual(error_response.status_code, 400)

    def test_malformed_json_returns_400(self):
        request = self.factory.post("/", data="{not valid json", content_type="application/json")
        data, error_response = parse_json_object_body(request)
        self.assertIsNone(data)
        self.assertEqual(error_response.status_code, 400)

    def test_invalid_utf8_returns_400_not_500(self):
        request = self.factory.generic(
            "POST", "/", data=b"\xff\xfe\xfd", content_type="application/json"
        )
        data, error_response = parse_json_object_body(request)
        self.assertIsNone(data)
        self.assertEqual(error_response.status_code, 400)

    def test_oversized_body_returns_400(self):
        oversized = '{"a": "' + ("x" * 100) + '"}'
        request = self.factory.post("/", data=oversized, content_type="application/json")
        data, error_response = parse_json_object_body(request, max_bytes=10)
        self.assertIsNone(data)
        self.assertEqual(error_response.status_code, 400)
