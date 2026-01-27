"""Tests for user search filters"""

import pytest

from crawl4weibo import WeiboClient
from crawl4weibo.models.user import User


@pytest.fixture()
def client():
    return WeiboClient(auto_fetch_cookies=False)


@pytest.mark.unit
class TestUserSearchFilters:
    def test_filter_by_gender_and_location(self, client):
        users = [
            User(id="1", screen_name="A", gender="m", location="Beijing"),
            User(id="2", screen_name="B", gender="f", location="Beijing"),
            User(id="3", screen_name="C", gender="m", location="Beijing"),
        ]

        filtered = client._filter_users(
            users,
            gender="male",
            location="beijing",
        )

        assert [user.id for user in filtered] == ["1", "3"]

    def test_filter_by_education_and_company(self, client):
        users = [
            User(
                id="1",
                screen_name="A",
                education="Test University",
                company="OpenAI",
            ),
            User(
                id="2",
                screen_name="B",
                education="Other School",
                company="Other",
            ),
        ]

        filtered = client._filter_users(
            users,
            education="university",
            company="openai",
        )

        assert [user.id for user in filtered] == ["1"]

    def test_filter_by_birthday_and_age_range(self, client):
        users = [User(id="1", screen_name="A", birthday="1995-02-03")]

        filtered = client._filter_users(users, birthday="1995")
        assert [user.id for user in filtered] == ["1"]

        age = client._calculate_age(1995, 2, 3)
        filtered = client._filter_users(users, age_range=(age, age))
        assert [user.id for user in filtered] == ["1"]

        filtered = client._filter_users(users, age_range=(age + 1, age + 2))
        assert filtered == []
