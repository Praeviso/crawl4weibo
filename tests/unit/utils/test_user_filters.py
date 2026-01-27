"""Tests for user filter helpers"""

from datetime import date

import pytest

from crawl4weibo.models.user import User
from crawl4weibo.utils import user_filters


@pytest.mark.unit
class TestUserFilters:
    def test_normalize_text(self):
        assert user_filters.normalize_text(None) == ""
        assert user_filters.normalize_text("  Bei Jing ") == "beijing"

    def test_match_text(self):
        assert user_filters.match_text("Beijing", "bei") is True
        assert user_filters.match_text("Beijing", None) is True
        assert user_filters.match_text(None, "bei") is False

    def test_normalize_gender_default(self):
        assert user_filters.normalize_gender("Unknown") == "unknown"

    def test_match_gender(self):
        assert user_filters.match_gender("m", "male") is True
        assert user_filters.match_gender(None, "male") is False
        assert user_filters.match_gender("f", None) is True

    def test_parse_birthday_parts(self):
        year, month, day = user_filters.parse_birthday_parts("1995-02-03")
        assert year == 1995
        assert month == 2
        assert day == 3

        year, month, day = user_filters.parse_birthday_parts("02-03")
        assert year is None
        assert month == 2
        assert day == 3

        year, month, day = user_filters.parse_birthday_parts("1995-13-40")
        assert year == 1995
        assert month is None
        assert day is None

    def test_calculate_age_with_fixed_date(self, monkeypatch):
        class FixedDate(date):
            @classmethod
            def today(cls):
                return cls(2025, 1, 15)

        monkeypatch.setattr(user_filters, "date", FixedDate)
        assert user_filters.calculate_age(2000, 2, 1) == 24
        assert user_filters.calculate_age(2000, None, None) == 25

    def test_normalize_age_range(self):
        assert user_filters.normalize_age_range(None) is None
        assert user_filters.normalize_age_range((None, None)) is None
        assert user_filters.normalize_age_range((18, 25)) == (18, 25)

        with pytest.raises(ValueError):
            user_filters.normalize_age_range((1,))

        with pytest.raises(ValueError):
            user_filters.normalize_age_range((-1, 10))

        with pytest.raises(ValueError):
            user_filters.normalize_age_range((10, 1))

    def test_match_birthday(self, monkeypatch):
        class FixedDate(date):
            @classmethod
            def today(cls):
                return cls(2025, 1, 15)

        monkeypatch.setattr(user_filters, "date", FixedDate)
        assert user_filters.match_birthday("1995-02-03", "1995", None) is True
        assert user_filters.match_birthday("1995-02-03", "1996", None) is False
        assert user_filters.match_birthday(None, "1995", None) is False
        assert user_filters.match_birthday("02-03", None, (20, 30)) is False
        assert user_filters.match_birthday("2000-02-01", None, (24, 24)) is True
        assert user_filters.match_birthday("2000-02-01", None, (25, 30)) is False

    def test_filter_users_empty_and_invalid_age_range(self):
        assert user_filters.filter_users([]) == []

        users = [User(id="1", screen_name="A", gender="m")]
        with pytest.raises(ValueError):
            user_filters.filter_users(users, age_range=(10, 5))
