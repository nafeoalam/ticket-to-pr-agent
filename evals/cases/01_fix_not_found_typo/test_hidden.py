import pytest


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_message_is_spelled_right(client, method):
    kwargs = {"json": {"title": "x"}} if method == "patch" else {}
    response = getattr(client, method)("/tasks/999", **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"
