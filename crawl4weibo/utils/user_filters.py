#!/usr/bin/env python

"""
User filtering helpers for crawl4weibo
"""

from __future__ import annotations

import re
from datetime import date

from ..models.user import User


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", "", value).lower()


def match_text(value: str | None, needle: str | None) -> bool:
    if not needle:
        return True
    if not value:
        return False
    return normalize_text(needle) in normalize_text(value)


def normalize_gender(value: str) -> str:
    normalized = re.sub(r"\s+", "", value).lower()
    gender_map = {
        "m": "m",
        "male": "m",
        "man": "m",
        "\u7537": "m",
        "f": "f",
        "female": "f",
        "woman": "f",
        "\u5973": "f",
    }
    return gender_map.get(normalized, normalized)


def match_gender(value: str | None, expected: str | None) -> bool:
    if not expected:
        return True
    normalized_expected = normalize_gender(expected)
    normalized_value = normalize_gender(value or "")
    return normalized_value == normalized_expected


def parse_birthday_parts(
    birthday: str | None,
) -> tuple[int | None, int | None, int | None]:
    if not birthday:
        return None, None, None

    text = birthday.strip()
    year = None
    month = None
    day = None

    year_match = re.search(r"(19|20)\d{2}", text)
    if year_match:
        year = int(year_match.group())
        remainder = text[year_match.end() :]
        numbers = re.findall(r"\d{1,2}", remainder)
    else:
        numbers = re.findall(r"\d{1,2}", text)

    if numbers:
        month = int(numbers[0])
    if len(numbers) > 1:
        day = int(numbers[1])

    if month is not None and not (1 <= month <= 12):
        month = None
    if day is not None and not (1 <= day <= 31):
        day = None

    return year, month, day


def calculate_age(year: int, month: int | None, day: int | None) -> int:
    today = date.today()
    age = today.year - year
    if (
        month is not None
        and day is not None
        and (today.month, today.day) < (month, day)
    ):
        age -= 1
    return age


def normalize_age_range(
    age_range: tuple[int | None, int | None] | None,
) -> tuple[int | None, int | None] | None:
    if age_range is None:
        return None

    if not isinstance(age_range, (tuple, list)) or len(age_range) != 2:
        raise ValueError("age_range must be a tuple/list of (min_age, max_age)")

    min_age, max_age = age_range
    if min_age is None and max_age is None:
        return None
    if min_age is not None and min_age < 0:
        raise ValueError("age_range min_age must be >= 0")
    if max_age is not None and max_age < 0:
        raise ValueError("age_range max_age must be >= 0")
    if min_age is not None and max_age is not None and min_age > max_age:
        raise ValueError("age_range min_age must be <= max_age")

    return min_age, max_age


def match_birthday(
    value: str | None,
    expected: str | None,
    age_range: tuple[int | None, int | None] | None,
) -> bool:
    if expected:
        if not value:
            return False
        if normalize_text(expected) not in normalize_text(value):
            return False

    if age_range:
        if not value:
            return False
        year, month, day = parse_birthday_parts(value)
        if not year:
            return False
        age = calculate_age(year, month, day)
        min_age, max_age = age_range
        if min_age is not None and age < min_age:
            return False
        if max_age is not None and age > max_age:
            return False

    return True


def filter_users(
    users: list[User],
    *,
    gender: str | None = None,
    location: str | None = None,
    birthday: str | None = None,
    age_range: tuple[int | None, int | None] | None = None,
    education: str | None = None,
    company: str | None = None,
) -> list[User]:
    if not users:
        return []

    normalized_age_range = normalize_age_range(age_range)
    filtered_users = []

    for user in users:
        if gender and not match_gender(user.gender, gender):
            continue
        if location and not match_text(user.location, location):
            continue
        if education and not match_text(user.education, education):
            continue
        if company and not match_text(user.company, company):
            continue
        if not match_birthday(user.birthday, birthday, normalized_age_range):
            continue
        filtered_users.append(user)

    return filtered_users
