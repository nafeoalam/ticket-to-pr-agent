def test_stats_when_empty(client):
    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json() == {"total": 0, "done": 0, "open": 0}


def test_stats_counts(client):
    for title in ["One", "Two", "Three"]:
        client.post("/tasks", json={"title": title})
    client.patch("/tasks/2", json={"done": True})
    assert client.get("/stats").json() == {"total": 3, "done": 1, "open": 2}
