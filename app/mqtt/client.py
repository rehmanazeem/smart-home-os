"""
Async MQTT client wrapper using asyncio-mqtt.

Sections:
0 - Imports
1 - AsyncMQTTClient (topic parsing lives in app.mqtt.topics)
"""

# =============================
# Section 0: Imports
# =============================
from typing import Optional

from asyncio_mqtt import Client, MqttError

from app.mqtt.topics import BASE_TOPIC, OtaStatus, StateUpdate, parse_message
from app.state.registry import DeviceRegistry


# =============================
# Section 1: AsyncMQTTClient
# =============================
class AsyncMQTTClient:
    """Thin async wrapper around an MQTT broker connection.

    Connects to the broker, subscribes to device topics, and feeds incoming
    relay/telemetry/OTA-status messages into the :class:`DeviceRegistry`.
    """

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, registry: Optional[DeviceRegistry] = None) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self._client: Optional[Client] = None
        self._connected = False
        self.registry = registry

    async def connect(self) -> None:
        """Open the connection to the configured MQTT broker."""
        self._client = Client(hostname=self.broker_host, port=self.broker_port)
        try:
            await self._client.connect()
            self._connected = True
        except MqttError:
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close the broker connection if currently connected."""
        if self._client and self._connected:
            await self._client.disconnect()
            self._connected = False

    async def handle_messages(self) -> None:
        """Subscribe to device topics and update registry state."""
        if not self._client:
            raise RuntimeError("MQTT client not connected")

        async with self._client.unfiltered_messages() as messages:
            # subscribe to broad topics including relay state and ota status
            await self._client.subscribe(f"{BASE_TOPIC}/+/+/+")
            await self._client.subscribe(f"{BASE_TOPIC}/+/ota/status")
            async for message in messages:
                try:
                    update = parse_message(message.topic, message.payload.decode())
                    if self.registry is None:
                        continue
                    if isinstance(update, StateUpdate):
                        await self.registry.update_device_state(update.device_id, update.state)
                    elif isinstance(update, OtaStatus):
                        await self.registry.update_ota_job_status(
                            update.job_id, update.device_id, update.status, update.info
                        )
                except Exception:
                    # ignore malformed
                    continue

    async def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> None:
        """Publish a string payload to the given topic (raises if not connected)."""
        if not self._client or not self._connected:
            raise RuntimeError("MQTT client not connected")
        await self._client.publish(topic, payload.encode(), qos=qos, retain=retain)
