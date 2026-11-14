import pytest


@pytest.fixture
def seeded(client):
    for number in range(60):
        client.post("/tasks", json={"title": f"Task {number:02d}"})
    return client


def test_default_limit_is_50(seeded):
    tasks = seeded.get("/tasks").json()
    assert len(tasks) == 50
    assert tasks[0]["title"] == "Task 00"


def test_limit_and_offset(seeded):
    tasks = seeded.get("/tasks?limit=10&offset=55").json()
    assert [task["title"] for task in tasks] == [f"Task {n}" for n in range(55, 60)]


def test_limit_of_100_is_allowed(seeded):
    assert len(seeded.get("/tasks?limit=100").json()) == 60


@pytest.mark.parametrize("query", ["limit=101", "limit=0", "offset=-1"])
def test_out_of_range_is_rejected(seeded, query):
    assert seeded.get(f"/tasks?{query}").status_code == 422
