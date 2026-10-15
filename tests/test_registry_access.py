import asyncio

from app.api.access import is_private_ip
from app.state.registry import DeviceRegistry


def test_is_private_ip():
    assert is_private_ip("192.168.1.5") and is_private_ip("10.1.2.3") and is_private_ip("127.0.0.1")
    assert not is_private_ip("8.8.8.8")
    assert not is_private_ip("not-an-ip")


def test_registry_roundtrip(tmp_path):
    async def run():
        path = tmp_path / "d.json"
        reg = DeviceRegistry(path)
        await reg.register_device("d1", {"room": "a"})
        await reg.register_device("d1", {"floor": 1})
        await reg.update_device_state("d1", {"relay/1/state": 1})
        job = await reg.create_ota_job(["d1"], "http://x/fw.bin", "1.0")
        await reg.update_ota_job_status(job, "d1", "success", {"k": 1})
        reg2 = DeviceRegistry(path)
        await reg2.load()
        d = await reg2.get_device("d1")
        assert d == {"meta": {"room": "a", "floor": 1}, "state": {"relay/1/state": 1}}
        assert (await reg2.get_ota_job(job))["devices"]["d1"] == {"status": "success", "info": {"k": 1}}

    asyncio.run(run())
