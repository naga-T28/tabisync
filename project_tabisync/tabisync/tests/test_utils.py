from django.test import RequestFactory, TestCase

from ..views.utils import (
    build_public_service_error_message,
    count_memo_words,
    get_client_ip,
    get_inclusive_day_count,
    ratelimit_client_ip,
    validate_checklist_limits,
    validate_memo_notes_limits,
)


class ClientIpTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_client_ip_prefers_cloudflare_header(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.10, 10.0.0.1",
            HTTP_CF_CONNECTING_IP="203.0.113.10",
        )

        self.assertEqual(get_client_ip(request), "203.0.113.10")

    def test_get_client_ip_falls_back_to_first_forwarded_ip(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.10, 10.0.0.1",
        )

        self.assertEqual(get_client_ip(request), "198.51.100.10")

    def test_ratelimit_client_ip_uses_same_resolution(self):
        request = self.factory.get("/", REMOTE_ADDR="198.51.100.10")

        self.assertEqual(ratelimit_client_ip(None, request), "198.51.100.10")

    def test_get_client_ip_ignores_invalid_proxy_headers(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="198.51.100.10",
            HTTP_X_FORWARDED_FOR="unknown, 198.51.100.20",
            HTTP_CF_CONNECTING_IP="not-an-ip",
        )

        self.assertEqual(get_client_ip(request), "198.51.100.20")


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
