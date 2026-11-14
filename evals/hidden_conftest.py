"""Copied next to each hidden test as conftest.py when a case is scored."""
import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app


@pytest.fixture
def client():
    store.reset()
    return TestClient(app)
