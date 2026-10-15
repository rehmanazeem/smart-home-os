/*
  Example ESP8266 sketch (Arduino core)
  - Connects to Wi-Fi
  - Connects to MQTT broker (on the Pi)
  - Subscribes to: home/demo/device/{deviceId}/relay/{id}/set
  - Publishes state to: home/demo/device/{deviceId}/relay/{id}/state
  - Publishes telemetry: home/demo/device/{deviceId}/telemetry
  - On OTA command (via MQTT) downloads firmware from orchestrator HTTP endpoint and performs update

  NOTE: This is a minimal example. Validate and secure before production use.
*/

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266httpUpdate.h>

// =============================
// Section 0: Configuration
// =============================
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
const char* mqtt_server = "192.168.1.100"; // set to your Pi
const char* deviceId = "demo-device-001";

WiFiClient espClient;
PubSubClient client(espClient);

// relays on GPIO4 and GPIO5
const int RELAY_PIN_1 = 4;
const int RELAY_PIN_2 = 5;

void publish_state(int relay, int value) {
  char topic[128];
  snprintf(topic, sizeof(topic), "home/demo/device/%s/relay/%d/state", deviceId, relay);
  char payload[32];
  snprintf(payload, sizeof(payload), "%d", value);
  client.publish(topic, payload);
}

void handle_command(char* topic, byte* payload, unsigned int length) {
  payload[length] = '\0';
  String t = String(topic);
  String p = String((char*)payload);
  // parse topic: home/demo/device/{deviceId}/relay/{id}/set
  // naive parsing
  if (t.indexOf("/relay/") > 0 && t.endsWith("/set")) {
    int start = t.indexOf("/relay/") + 7;
    int slash = t.indexOf('/', start);
    String relayIdStr = t.substring(start, slash);
    int relayId = relayIdStr.toInt();
    int value = p.toInt();
    int pin = (relayId == 1) ? RELAY_PIN_1 : RELAY_PIN_2;
    digitalWrite(pin, value ? LOW : HIGH); // assume active low
    publish_state(relayId, value);
  } else if (t.endsWith("/ota")) {
    // payload expected to be JSON: {"url":"http://.../esp32.bin", "job_id":"..."}
    String url = p;
    String job_id = "";
    // attempt to extract job_id and url from JSON-like payload (naive parsing)
    int jpos = p.indexOf("\"job_id\"");
    if (jpos > 0) {
      int colon = p.indexOf(':', jpos);
      int q1 = p.indexOf('"', colon + 1);
      int q2 = p.indexOf('"', q1 + 1);
      if (q1 > 0 && q2 > q1) job_id = p.substring(q1 + 1, q2);
    }

    // publish started status
    char statusTopic[128];
    snprintf(statusTopic, sizeof(statusTopic), "home/demo/device/%s/ota/status", deviceId);
    char statusPayload[256];
    snprintf(statusPayload, sizeof(statusPayload), "{\"job_id\":\"%s\",\"status\":\"started\"}", job_id.c_str());
    client.publish(statusTopic, statusPayload);

    // attempt http update (will reboot on success)
    t_httpUpdate_return ret = ESPhttpUpdate.update(url);
    if (ret == HTTP_UPDATE_OK) {
      // on success the module will reboot; try to publish success but it may not run
      snprintf(statusPayload, sizeof(statusPayload), "{\"job_id\":\"%s\",\"status\":\"success\"}", job_id.c_str());
      client.publish(statusTopic, statusPayload);
    } else {
      // publish failure with code
      snprintf(statusPayload, sizeof(statusPayload), "{\"job_id\":\"%s\",\"status\":\"failed\",\"info\":{\"code\":%d}}", job_id.c_str(), (int)ret);
      client.publish(statusTopic, statusPayload);
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect(deviceId)) {
      // subscribe
      client.subscribe((String("home/demo/device/") + deviceId + "/relay/+/set").c_str());
      client.subscribe((String("home/demo/device/") + deviceId + "/ota").c_str());
    } else {
      delay(2000);
    }
  }
}

void setup() {
  pinMode(RELAY_PIN_1, OUTPUT);
  pinMode(RELAY_PIN_2, OUTPUT);
  digitalWrite(RELAY_PIN_1, HIGH);
  digitalWrite(RELAY_PIN_2, HIGH);

  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  client.setServer(mqtt_server, 1883);
  client.setCallback([](char* topic, byte* payload, unsigned int length){ handle_command(topic, payload, length); });
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // publish periodic telemetry
  static unsigned long last = 0;
  if (millis() - last > 30000) {
    last = millis();
    char topic[128];
    snprintf(topic, sizeof(topic), "home/demo/device/%s/telemetry", deviceId);
    char payload[128];
    snprintf(payload, sizeof(payload), "{\"rssi\":%d}", WiFi.RSSI());
    client.publish(topic, payload);
  }
}
