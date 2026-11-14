def test_done_can_be_set_back_to_false(client):
    task = client.post("/tasks", json={"title": "Oops"}).json()
    client.patch(f"/tasks/{task['id']}", json={"done": True})
    response = client.patch(f"/tasks/{task['id']}", json={"done": False})
    assert response.status_code == 200
    assert response.json()["done"] is False
    assert client.get(f"/tasks/{task['id']}").json()["done"] is False


def test_done_true_still_works(client):
    task = client.post("/tasks", json={"title": "Fine"}).json()
    assert client.patch(f"/tasks/{task['id']}", json={"done": True}).json()["done"] is True
