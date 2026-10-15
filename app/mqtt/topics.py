"""Pure MQTT topic builders and incoming-message parsing (no broker needed)."""

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

BASE_TOPIC = "home/demo/device"


def relay_set_topic(device_id: str, relay_id: int) -> str:
    """Topic for commanding a device relay."""
    return f"{BASE_TOPIC}/{device_id}/relay/{relay_id}/set"


def ota_topic(device_id: str) -> str:
    """Topic for sending an OTA command to a device."""
    return f"{BASE_TOPIC}/{device_id}/ota"


@dataclass
class StateUpdate:
    """A component state value reported by a device."""
    device_id: str
    state: Dict[str, Any]


@dataclass
class OtaStatus:
    """An OTA progress report; ``info`` is the optional detail dict."""
    device_id: str
    job_id: str
    status: str
    info: Optional[Any]


def _loads_or_raw(payload: str) -> Any:
    try:
        return json.loads(payload)
    except Exception:
        return payload


def parse_message(topic: str, payload: str) -> Optional[Union[StateUpdate, OtaStatus]]:
    """Map an incoming device message to a registry update, or None if it is ignored."""
    parts = topic.split("/")
    # parts: [home, demo, device, {deviceId}, {component}, {id}, {key}]
    if len(parts) >= 7 and parts[2] == "device":
        device_id, component, comp_id, key = parts[3], parts[4], parts[5], parts[6]
        return StateUpdate(device_id, {f"{component}/{comp_id}/{key}": _loads_or_raw(payload)})
    # ota status: home/demo/device/{deviceId}/ota/status
    if len(parts) >= 6 and parts[2] == "device" and parts[4] == "ota" and parts[5] == "status":
        try:
            obj = json.loads(payload)
        except Exception:
            obj = {"status": payload}
        if isinstance(obj, dict) and obj.get("job_id") and obj.get("status"):
            return OtaStatus(parts[3], obj["job_id"], obj["status"], obj.get("info"))
    return None
