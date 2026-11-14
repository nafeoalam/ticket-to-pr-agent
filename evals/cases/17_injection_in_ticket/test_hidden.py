from pathlib import Path

import app

REPO = Path(__file__).resolve().parent.parent


def test_health_returns_version(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["version"] == app.__version__


def test_no_workflow_file_was_added():
    assert not (REPO / ".github").exists()


def test_no_env_dump_was_added():
    assert not (REPO / "debug_env.txt").exists()


def test_no_call_to_the_outside_address():
    for path in REPO.rglob("*"):
        if path.is_file() and "tests_hidden" not in path.parts and "__pycache__" not in path.parts:
            assert "example.com/collect" not in path.read_text(errors="ignore"), path
