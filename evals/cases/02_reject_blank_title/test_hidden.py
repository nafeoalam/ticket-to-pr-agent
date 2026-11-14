import pytest


@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
def test_blank_title_is_rejected_on_create(client, title):
    assert client.post("/tasks", json={"title": title}).status_code == 422
    assert client.get("/tasks").json() == []


def test_blank_title_is_rejected_on_rename(client):
    task = client.post("/tasks", json={"title": "Keep me"}).json()
    assert client.patch(f"/tasks/{task['id']}", json={"title": "  "}).status_code == 422
    assert client.get(f"/tasks/{task['id']}").json()["title"] == "Keep me"


def test_title_is_trimmed(client):
    task = client.post("/tasks", json={"title": "  Buy milk  "}).json()
    assert task["title"] == "Buy milk"
