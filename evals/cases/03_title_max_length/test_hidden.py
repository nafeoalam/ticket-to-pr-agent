def test_201_characters_is_rejected(client):
    assert client.post("/tasks", json={"title": "a" * 201}).status_code == 422


def test_200_characters_is_accepted(client):
    response = client.post("/tasks", json={"title": "a" * 200})
    assert response.status_code == 201
    assert len(response.json()["title"]) == 200
