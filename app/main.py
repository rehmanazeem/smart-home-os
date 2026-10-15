"""
FastAPI orchestrator entrypoint.

Sections are clearly marked.
"""

# =============================
# Section 0: Imports
# =============================
import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.mqtt.client import AsyncMQTTClient
from app.state.registry import DeviceRegistry
from app.api.devices import router as devices_router
from app.api.ota import router as ota_router


# =============================
# Section 1: Configuration
# =============================
BASE_DIR = Path(__file__).resolve().parents[1]
FIRMWARE_DIR = BASE_DIR / "firmware"
FIRMWARE_BIN = FIRMWARE_DIR / "esp32.bin"
REGISTRY_FILE = BASE_DIR / "data" / "devices.json"


# =============================
# Section 2: App factory
# =============================
def create_app() -> FastAPI:
    """Build and configure the SmartHome OS FastAPI application.

    Wires up the device and OTA routers, initialises the registry and MQTT
    client on startup, and exposes the firmware download endpoint.
    """
    app = FastAPI(title="SmartHome OS")

    # attach objects during startup
    app.include_router(devices_router, prefix="/api")
    app.include_router(ota_router, prefix="/api")

    @app.on_event("startup")
    async def startup_event() -> None:
        # ensure data dir
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)

        # setup registry
        app.state.registry = DeviceRegistry(path=REGISTRY_FILE)
        await app.state.registry.load()

        # setup mqtt client
        app.state.mqtt = AsyncMQTTClient(broker_host="localhost", registry=app.state.registry)
        await app.state.mqtt.connect()
        # start background message loop
        app.state._mqtt_task = asyncio.create_task(app.state.mqtt.handle_messages())

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        # gracefully stop mqtt
        if hasattr(app.state, "mqtt"):
            await app.state.mqtt.disconnect()
        if hasattr(app.state, "_mqtt_task"):
            app.state._mqtt_task.cancel()

    # firmware serving endpoint (should be reachable only via VPN interface)
    @app.get("/firmware/esp32.bin")
    async def firmware_bin() -> Any:
        if not FIRMWARE_BIN.exists():
            return {"detail": "firmware not found"}
        return FileResponse(path=str(FIRMWARE_BIN), media_type="application/octet-stream", filename="esp32.bin")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
