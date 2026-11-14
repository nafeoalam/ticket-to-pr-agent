def test_empty_patch_is_rejected(client):
    task = client.post("/tasks", json={"title": "Same"}).json()
    response = client.patch(f"/tasks/{task['id']}", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "No fields to update"


def test_missing_task_is_404(client):
    assert client.patch("/tasks/999", json={}).status_code == 404


def test_real_patch_still_works(client):
    task = client.post("/tasks", json={"title": "Old"}).json()
    assert client.patch(f"/tasks/{task['id']}", json={"title": "New"}).json()["title"] == "New"
