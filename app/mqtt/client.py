"""
Async MQTT client wrapper using asyncio-mqtt.

Sections:
0 - Imports
1 - Topic/schema helpers
2 - AsyncMQTTClient
"""

# =============================
# Section 0: Imports
# =============================
import asyncio
import json
from typing import Optional

from asyncio_mqtt import Client, MqttError

from app.state.registry import DeviceRegistry


# =============================
# Section 1: Topic helpers
# =============================
BASE_TOPIC = "home/demo/device"


# =============================
# Section 2: AsyncMQTTClient
# =============================
class AsyncMQTTClient:
    """Thin async wrapper around an MQTT broker connection.

    Connects to the broker, subscribes to device topics, and feeds incoming
    relay/telemetry/OTA-status messages into the :class:`DeviceRegistry`.
    """

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, registry: Optional[DeviceRegistry] = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self._client: Optional[Client] = None
        self._connected = False
        self.registry = registry

    async def connect(self):
        """Open the connection to the configured MQTT broker."""
        self._client = Client(hostname=self.broker_host, port=self.broker_port)
        try:
            await self._client.connect()
            self._connected = True
        except MqttError:
            self._connected = False
            raise

    async def disconnect(self):
        """Close the broker connection if currently connected."""
        if self._client and self._connected:
            await self._client.disconnect()
            self._connected = False

    async def handle_messages(self):
        """Subscribe to device topics and update registry state."""
        if not self._client:
            raise RuntimeError("MQTT client not connected")

        async with self._client.unfiltered_messages() as messages:
            # subscribe to broad topics including relay state and ota status
            await self._client.subscribe(f"{BASE_TOPIC}/+/+/+")
            await self._client.subscribe(f"{BASE_TOPIC}/+/ota/status")
            async for message in messages:
                topic = message.topic
                payload = message.payload.decode()
                parts = topic.split("/")
                try:
                    # parts: [home, demo, device, {deviceId}, relay, {id}, state]
                    if len(parts) >= 7 and parts[2] == "device":
                        device_id = parts[3]
                        component = parts[4]
                        comp_id = parts[5]
                        key = parts[6]
                        data = payload
                        try:
                            data = json.loads(payload)
                        except Exception:
                            pass
                        if self.registry:
                            # for relay/state messages, merge into device state
                            if component == "relay":
                                await self.registry.update_device_state(device_id, {f"relay/{comp_id}/{key}": data})
                            else:
                                await self.registry.update_device_state(device_id, {f"{component}/{comp_id}/{key}": data})
                    # ota status messages: home/demo/device/{deviceId}/ota/status
                    elif len(parts) >= 5 and parts[2] == "device" and parts[4] == "ota" and parts[5] == "status":
                        device_id = parts[3]
                        # payload expected JSON: {"job_id":"...", "status":"started|success|failed", "info":{}}
                        try:
                            obj = json.loads(payload)
                        except Exception:
                            obj = {"status": payload}
                        if self.registry and isinstance(obj, dict):
                            job_id = obj.get("job_id")
                            status = obj.get("status")
                            info = obj.get("info")
                            if job_id and status:
                                await self.registry.update_ota_job_status(job_id, device_id, status, info)
                except Exception:
                    # ignore malformed
                    continue

    async def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """Publish a string payload to the given topic (raises if not connected)."""
        if not self._client or not self._connected:
            raise RuntimeError("MQTT client not connected")
        await self._client.publish(topic, payload.encode(), qos=qos, retain=retain)
