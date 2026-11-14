def test_delete_returns_204_and_no_body(client):
    task = client.post("/tasks", json={"title": "Remove me"}).json()
    response = client.delete(f"/tasks/{task['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_delete_missing_task_is_still_404(client):
    assert client.delete("/tasks/999").status_code == 404
