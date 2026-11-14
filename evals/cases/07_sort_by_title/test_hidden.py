import pytest


@pytest.fixture
def seeded(client):
    for title in ["banana", "Apple", "cherry"]:
        client.post("/tasks", json={"title": title})
    return client


def titles(response):
    assert response.status_code == 200
    return [task["title"] for task in response.json()]


def test_default_is_creation_order(seeded):
    assert titles(seeded.get("/tasks")) == ["banana", "Apple", "cherry"]


def test_sort_by_title_ignores_case(seeded):
    assert titles(seeded.get("/tasks?sort=title")) == ["Apple", "banana", "cherry"]


def test_sort_by_title_descending(seeded):
    assert titles(seeded.get("/tasks?sort=title&order=desc")) == ["cherry", "banana", "Apple"]


def test_created_at_descending(seeded):
    assert titles(seeded.get("/tasks?sort=created_at&order=desc")) == ["cherry", "Apple", "banana"]


@pytest.mark.parametrize("query", ["sort=color", "order=sideways"])
def test_unknown_values_are_rejected(seeded, query):
    assert seeded.get(f"/tasks?{query}").status_code == 422
