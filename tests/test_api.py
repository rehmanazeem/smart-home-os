import pytest

from fastapi.testclient import TestClient

from app.main import create_app


def test_list_devices_empty():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)
