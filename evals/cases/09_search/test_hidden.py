import pytest


@pytest.fixture
def seeded(client):
    client.post("/tasks", json={"title": "Write REPORT", "description": "for the board"})
    client.post("/tasks", json={"title": "Call supplier", "description": "ask about the late report"})
    client.post("/tasks", json={"title": "Book flights"})
    return client


def ids(response):
    assert response.status_code == 200
    return [task["id"] for task in response.json()]


def test_matches_title_and_description(seeded):
    assert ids(seeded.get("/tasks?q=report")) == [1, 2]


def test_case_does_not_matter(seeded):
    assert ids(seeded.get("/tasks?q=FLIGHTS")) == [3]


def test_no_match(seeded):
    assert ids(seeded.get("/tasks?q=zebra")) == []


def test_without_q_returns_all(seeded):
    assert ids(seeded.get("/tasks")) == [1, 2, 3]
