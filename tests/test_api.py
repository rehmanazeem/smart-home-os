import pytest

from fastapi.testclient import TestClient

from app.main import create_app
from app.state.registry import DeviceRegistry


def test_list_devices_empty():
    app = create_app()
    app.state.registry = DeviceRegistry()  # TestClient without lifespan skips startup
    client = TestClient(app)
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)
