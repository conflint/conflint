"""Utility function tests."""

from __future__ import annotations

from conflint.utils import (
    close_matches,
    is_sensitive_name,
    looks_like_secret,
    shannon_entropy,
    strip_quotes,
)


class TestStripQuotes:
    def test_matching_quotes_removed(self):
        assert strip_quotes("'hello'") == "hello"
        assert strip_quotes('"hello"') == "hello"

    def test_unbalanced_left_alone(self):
        assert strip_quotes("'hello") == "'hello"
        assert strip_quotes("hello'") == "hello'"

    def test_plain_value(self):
        assert strip_quotes("hello") == "hello"


class TestLevenshtein:
    def test_close_matches_ranking(self):
        matches = close_matches("DBHOST", ["DB_HOST", "HOST"])
        assert matches[0][0] == "DB_HOST"
        assert matches[0][1] == 1

    def test_no_close_match(self):
        assert close_matches("QQZZ", ["AAAA"]) == []


class TestEntropy:
    def test_low_entropy(self):
        assert shannon_entropy("password") < 3.5

    def test_high_entropy(self):
        assert shannon_entropy("xK9#mP2!qR7#vL4&zZ8") > 3.8


class TestLooksLikeSecret:
    def test_sensitive_names(self):
        assert is_sensitive_name("PASSWORD") is True
        assert is_sensitive_name("API_KEY") is True
        assert is_sensitive_name("PORT") is False
        assert is_sensitive_name("DEBUG") is False

    def test_placeholder_value_rejected(self):
        assert looks_like_secret("password") is False

    def test_short_value_rejected(self):
        assert looks_like_secret("abc") is False

    def test_high_entropy_value_accepted(self):
        assert looks_like_secret("xK9#mP2!qR7#vL4&zZ8") is True

    def test_empty_value_rejected(self):
        assert looks_like_secret("") is False
        assert looks_like_secret(None) is False
