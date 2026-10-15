"""
Device registry and state cache.

Sections:
0 - Imports
1 - DeviceRegistry implementation
"""

# =============================
# Section 0: Imports
# =============================
import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, List


# =============================
# Section 1: DeviceRegistry
# =============================
class DeviceRegistry:
    """In-memory device/state cache backed by an optional JSON file.

    Tracks per-device metadata and last-known state plus OTA job records.
    All mutating operations are guarded by an asyncio lock and persisted via
    :meth:`save`.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._path = Path(path) if path else None
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        """Load the registry from the backing JSON file if it exists."""
        if self._path and self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                async with self._lock:
                    self._devices = data
            except Exception:
                self._devices = {}

    async def save(self) -> None:
        """Persist the current registry contents to the backing JSON file."""
        if not self._path:
            return
        async with self._lock:
            self._path.write_text(json.dumps(self._devices, indent=2))

    async def list_devices(self) -> Dict[str, Dict[str, Any]]:
        """Return a shallow copy of all stored device entries."""
        async with self._lock:
            return dict(self._devices)

    async def register_device(self, device_id: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Create a device entry, or merge new metadata into an existing one."""
        async with self._lock:
            if device_id not in self._devices:
                self._devices[device_id] = {"meta": meta or {}, "state": {}}
            else:
                # merge meta
                self._devices[device_id].setdefault("meta", {}).update(meta or {})
        await self.save()

    # =============================
    # OTA job management
    # =============================
    async def create_ota_job(self, device_ids: List[str], url: str, version: Optional[str] = None) -> str:
        """Create an OTA job and mark devices as pending."""
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "url": url,
            "version": version,
            "devices": {d: {"status": "pending"} for d in device_ids},
        }
        async with self._lock:
            if "ota_jobs" not in self._devices:
                # store jobs under a special key
                self._devices.setdefault("_meta", {})
                self._devices.setdefault("ota_jobs", {})
            self._devices.setdefault("ota_jobs", {})[job_id] = job
        await self.save()
        return job_id

    async def list_ota_jobs(self) -> Dict[str, Any]:
        """Return all known OTA jobs keyed by job id."""
        async with self._lock:
            return dict(self._devices.get("ota_jobs", {}))

    async def get_ota_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return a single OTA job by id, or ``None`` if it does not exist."""
        async with self._lock:
            return self._devices.get("ota_jobs", {}).get(job_id)

    async def update_ota_job_status(self, job_id: str, device_id: str, status: str, info: Optional[Dict[str, Any]] = None) -> None:
        """Update the status (and optional info) of one device within an OTA job."""
        async with self._lock:
            jobs = self._devices.setdefault("ota_jobs", {})
            job = jobs.get(job_id)
            if not job:
                return
            job_devices = job.setdefault("devices", {})
            job_devices.setdefault(device_id, {})
            job_devices[device_id]["status"] = status
            if info:
                job_devices[device_id].setdefault("info", {}).update(info)
        await self.save()

    async def update_device_state(self, device_id: str, state: Dict[str, Any]) -> None:
        """Shallow-merge reported state into a device, creating it if needed."""
        async with self._lock:
            if device_id not in self._devices:
                self._devices[device_id] = {"meta": {}, "state": {}}
            # shallow merge
            self._devices[device_id]["state"].update(state)
        await self.save()

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Return a single device entry by id, or ``None`` if not present."""
        async with self._lock:
            return self._devices.get(device_id)
