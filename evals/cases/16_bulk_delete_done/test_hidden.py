import pytest


@pytest.fixture
def seeded(client):
    for title in ["Open", "Done A", "Done B"]:
        client.post("/tasks", json={"title": title})
    client.patch("/tasks/2", json={"done": True})
    client.patch("/tasks/3", json={"done": True})
    return client


def test_deletes_only_finished_tasks(seeded):
    response = seeded.delete("/tasks?done=true")
    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert [task["title"] for task in seeded.get("/tasks").json()] == ["Open"]


def test_count_is_zero_when_nothing_is_done(client):
    client.post("/tasks", json={"title": "Open"})
    assert client.delete("/tasks?done=true").json() == {"deleted": 0}


@pytest.mark.parametrize("url", ["/tasks", "/tasks?done=false"])
def test_refuses_without_done_true(seeded, url):
    assert seeded.delete(url).status_code == 400
    assert len(seeded.get("/tasks").json()) == 3


def test_delete_by_id_still_works(seeded):
    assert seeded.delete("/tasks/1").status_code in (200, 204)
    assert seeded.get("/tasks/1").status_code == 404
