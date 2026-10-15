import os
import json

from fastapi.testclient import TestClient

from app.main import create_app


def test_publish_ota_no_devices(tmp_path, monkeypatch):
    app = create_app()
    client = TestClient(app)

    # ensure no devices
    resp = client.post("/api/ota/publish", json={})
    assert resp.status_code == 400 or resp.status_code == 403


def test_publish_ota_with_api_key(monkeypatch):
    # set API key and create a dummy mqtt publisher on app.state
    monkeypatch.setenv("SMARTHOME_API_KEY", "secret-token")
    app = create_app()
    client = TestClient(app)

    class DummyMQTT:
        async def publish(self, topic, payload, qos=0, retain=False):
            # pretend publishing worked
            return None

    # attach dummy mqtt and registry with a device
    app.state.mqtt = DummyMQTT()

    class DummyRegistry:
        async def list_devices(self):
            return {"demo-device-001": {}}

        async def create_ota_job(self, device_ids, url, version=None):
            return "job-1"

    app.state.registry = DummyRegistry()

    headers = {"x-api-key": "secret-token"}
    resp = client.post("/api/ota/publish", json={"device_ids": ["demo-device-001"]}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert "results" in data
