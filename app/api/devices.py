"""
Devices API router.

Sections:
0 - Imports
1 - Router & endpoints
"""

# =============================
# Section 0: Imports
# =============================
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.mqtt.topics import relay_set_topic
from app.state.registry import DeviceRegistry

router = APIRouter()


# =============================
# Section 1: Router & endpoints
# =============================


class RegisterPayload(BaseModel):
    device_id: str
    meta: Optional[Dict[str, Any]] = None


@router.get("/devices")
async def list_devices(request: Request) -> Dict[str, Dict[str, Any]]:
    """Return all known devices and their cached state."""
    registry: DeviceRegistry = request.app.state.registry
    devices = await registry.list_devices()
    return devices


@router.post("/devices/register")
async def register_device(payload: RegisterPayload, request: Request) -> Dict[str, str]:
    """Register a new device (or merge metadata into an existing one)."""
    registry: DeviceRegistry = request.app.state.registry
    await registry.register_device(payload.device_id, payload.meta)
    return {"status": "ok", "device_id": payload.device_id}


@router.post("/devices/{device_id}/relay/{relay_id}/set")
async def set_relay(device_id: str, relay_id: int, value: int, request: Request) -> Dict[str, Any]:
    """Request to set a relay value (0/1). This publishes an MQTT command."""
    mqtt = request.app.state.mqtt
    topic = relay_set_topic(device_id, relay_id)
    payload = {"value": int(value)}
    try:
        await mqtt.publish(topic, json.dumps(payload))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "sent", "topic": topic, "payload": payload}
