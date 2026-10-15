"""
OTA publish router.

Sections:
0 - Imports
1 - Router (access control lives in app.api.access)
"""

# =============================
# Section 0: Imports
# =============================
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, AnyUrl

from app.api.access import check_access
from app.mqtt.topics import ota_topic

router = APIRouter()


# =============================
# Section 1: Router
# =============================


class OTAPayload(BaseModel):
    device_ids: Optional[List[str]] = None
    url: Optional[AnyUrl] = None
    version: Optional[str] = None


@router.post("/ota/publish")
async def publish_ota(payload: OTAPayload, request: Request) -> Dict[str, Any]:
    """Publish an OTA command to one or more devices.

    Protection: either set SMARTHOME_API_KEY env var and provide the same in X-API-KEY header,
    or ensure the request comes from a private IP (VPN / local network).
    """
    if not check_access(request):
        raise HTTPException(status_code=403, detail="forbidden")

    # default firmware url served by orchestrator
    base_url = f"http://{request.url.hostname}:{request.url.port or 80}/firmware/esp32.bin"
    firmware_url = str(payload.url) if payload.url else base_url

    mqtt = request.app.state.mqtt
    registry = request.app.state.registry

    # determine devices
    if payload.device_ids:
        target_devices = payload.device_ids
    else:
        devices = await registry.list_devices()
        target_devices = list(devices.keys())

    if not target_devices:
        raise HTTPException(status_code=400, detail="no target devices")

    # create an OTA job in registry
    job_id = await registry.create_ota_job(target_devices, firmware_url, payload.version)

    results: List[Dict[str, Any]] = []
    for device_id in target_devices:
        topic = ota_topic(device_id)
        message = {"url": firmware_url, "job_id": job_id}
        if payload.version:
            message["version"] = payload.version
        try:
            # use QoS 1 for better delivery guarantee (broker and client must support it)
            await mqtt.publish(topic, json.dumps(message))
            results.append({"device": device_id, "status": "sent", "topic": topic})
        except Exception as e:
            results.append({"device": device_id, "status": "error", "error": str(e)})

    return {"job_id": job_id, "results": results}
