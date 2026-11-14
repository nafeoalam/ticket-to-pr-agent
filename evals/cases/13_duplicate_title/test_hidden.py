def test_duplicate_open_title_is_rejected(client):
    assert client.post("/tasks", json={"title": "Pay rent"}).status_code == 201
    assert client.post("/tasks", json={"title": "pay RENT"}).status_code == 409
    assert len(client.get("/tasks").json()) == 1


def test_allowed_when_the_other_one_is_done(client):
    first = client.post("/tasks", json={"title": "Pay rent"}).json()
    client.patch(f"/tasks/{first['id']}", json={"done": True})
    assert client.post("/tasks", json={"title": "Pay rent"}).status_code == 201


def test_different_titles_are_fine(client):
    assert client.post("/tasks", json={"title": "Pay rent"}).status_code == 201
    assert client.post("/tasks", json={"title": "Pay rent for March"}).status_code == 201
