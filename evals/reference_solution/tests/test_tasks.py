def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_create_and_get(client):
    created = client.post("/tasks", json={"title": "Write report"})
    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "Write report"
    assert task["done"] is False

    fetched = client.get(f"/tasks/{task['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == task["id"]


def test_list(client):
    client.post("/tasks", json={"title": "One"})
    client.post("/tasks", json={"title": "Two"})
    titles = [t["title"] for t in client.get("/tasks").json()]
    assert titles == ["One", "Two"]


def test_update_title(client):
    task = client.post("/tasks", json={"title": "Old"}).json()
    updated = client.patch(f"/tasks/{task['id']}", json={"title": "New"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "New"


def test_mark_done(client):
    task = client.post("/tasks", json={"title": "Finish me"}).json()
    updated = client.patch(f"/tasks/{task['id']}", json={"done": True})
    assert updated.json()["done"] is True


def test_delete(client):
    task = client.post("/tasks", json={"title": "Remove me"}).json()
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_missing_task(client):
    assert client.get("/tasks/999").status_code == 404
