from app.mqtt.topics import OtaStatus, StateUpdate, ota_topic, parse_message, relay_set_topic


def test_topic_builders():
    assert relay_set_topic("d1", 2) == "home/demo/device/d1/relay/2/set"
    assert ota_topic("d1") == "home/demo/device/d1/ota"


def test_relay_state_json_and_raw():
    t = "home/demo/device/d1/relay/1/state"
    assert parse_message(t, "1") == StateUpdate("d1", {"relay/1/state": 1})
    assert parse_message(t, "on") == StateUpdate("d1", {"relay/1/state": "on"})


def test_ota_status():
    t = "home/demo/device/d1/ota/status"
    msg = '{"job_id": "j", "status": "success", "info": {"v": "1"}}'
    assert parse_message(t, msg) == OtaStatus("d1", "j", "success", {"v": "1"})
    assert parse_message(t, "garbage") is None
    assert parse_message(t, '{"status": "x"}') is None


def test_ignored_topics():
    assert parse_message("home/demo/device/d1/telemetry", "{}") is None
    assert parse_message("other/x", "{}") is None
