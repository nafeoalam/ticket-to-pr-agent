from datetime import datetime


def test_completed_at_starts_as_null(client):
    task = client.post("/tasks", json={"title": "Fresh"}).json()
    assert "completed_at" in task
    assert task["completed_at"] is None


def test_complete_sets_done_and_time(client):
    task = client.post("/tasks", json={"title": "Finish"}).json()
    response = client.post(f"/tasks/{task['id']}/complete")
    assert response.status_code == 200
    body = response.json()
    assert body["done"] is True
    datetime.fromisoformat(body["completed_at"].replace("Z", "+00:00"))
    assert client.get(f"/tasks/{task['id']}").json()["completed_at"] == body["completed_at"]


def test_completing_twice_keeps_the_first_time(client):
    task = client.post("/tasks", json={"title": "Twice"}).json()
    first = client.post(f"/tasks/{task['id']}/complete").json()["completed_at"]
    again = client.post(f"/tasks/{task['id']}/complete")
    assert again.status_code == 200
    assert again.json()["completed_at"] == first


def test_missing_task(client):
    assert client.post("/tasks/999/complete").status_code == 404
