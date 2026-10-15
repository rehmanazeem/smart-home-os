"""
Devices API router.

Sections:
0 - Imports
1 - Router & endpoints
"""

# =============================
# Section 0: Imports
# =============================
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json

from app.state.registry import DeviceRegistry

router = APIRouter()


# =============================
# Section 1: Router & endpoints
# =============================


class RegisterPayload(BaseModel):
    device_id: str
    meta: dict | None = None


@router.get("/devices")
async def list_devices():
    """Return all known devices and their cached state."""
    registry: DeviceRegistry = router.app.state.registry  # type: ignore
    devices = await registry.list_devices()
    return devices


@router.post("/devices/register")
async def register_device(payload: RegisterPayload):
    """Register a new device (or merge metadata into an existing one)."""
    registry: DeviceRegistry = router.app.state.registry  # type: ignore
    await registry.register_device(payload.device_id, payload.meta)
    return {"status": "ok", "device_id": payload.device_id}


@router.post("/devices/{device_id}/relay/{relay_id}/set")
async def set_relay(device_id: str, relay_id: int, value: int):
    """Request to set a relay value (0/1). This publishes an MQTT command."""
    mqtt = router.app.state.mqtt  # type: ignore
    topic = f"home/demo/device/{device_id}/relay/{relay_id}/set"
    payload = {"value": int(value)}
    try:
        await mqtt.publish(topic, json.dumps(payload))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "sent", "topic": topic, "payload": payload}
