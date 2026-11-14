def test_default_is_empty_list(client):
    assert client.post("/tasks", json={"title": "No tags"}).json()["tags"] == []


def test_tags_are_cleaned(client):
    body = {"title": "Tagged", "tags": ["Work", " urgent ", "work", "", "URGENT", "home"]}
    task = client.post("/tasks", json=body).json()
    assert task["tags"] == ["work", "urgent", "home"]
    assert client.get(f"/tasks/{task['id']}").json()["tags"] == ["work", "urgent", "home"]


def test_filter_by_tag(client):
    client.post("/tasks", json={"title": "A", "tags": ["work"]})
    client.post("/tasks", json={"title": "B", "tags": ["home"]})
    client.post("/tasks", json={"title": "C", "tags": ["home", "work"]})
    assert [t["title"] for t in client.get("/tasks?tag=work").json()] == ["A", "C"]
    assert [t["title"] for t in client.get("/tasks?tag=HOME").json()] == ["B", "C"]
    assert client.get("/tasks?tag=nothing").json() == []
