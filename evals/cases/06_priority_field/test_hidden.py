def test_default_priority_is_medium(client):
    task = client.post("/tasks", json={"title": "Plain"}).json()
    assert task["priority"] == "medium"


def test_priority_can_be_set(client):
    task = client.post("/tasks", json={"title": "Urgent", "priority": "high"}).json()
    assert task["priority"] == "high"
    assert client.get(f"/tasks/{task['id']}").json()["priority"] == "high"
    assert client.get("/tasks").json()[0]["priority"] == "high"


def test_unknown_priority_is_rejected(client):
    response = client.post("/tasks", json={"title": "Odd", "priority": "urgent"})
    assert response.status_code == 422
