import pytest


@pytest.fixture
def seeded(client):
    for title in ["Open one", "Done one", "Open two"]:
        client.post("/tasks", json={"title": title})
    client.patch("/tasks/2", json={"done": True})
    return client


def titles(response):
    return [task["title"] for task in response.json()]


def test_only_done(seeded):
    assert titles(seeded.get("/tasks?done=true")) == ["Done one"]


def test_only_open(seeded):
    assert titles(seeded.get("/tasks?done=false")) == ["Open one", "Open two"]


def test_no_filter_returns_all(seeded):
    assert len(seeded.get("/tasks").json()) == 3


def test_bad_value(seeded):
    assert seeded.get("/tasks?done=maybe").status_code == 422
