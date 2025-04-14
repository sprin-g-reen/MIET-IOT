#include <WiFi.h>
#include <HTTPClient.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// Wi-Fi credentials
const char* ssid = "Airtel_Springreen";
const char* password = "Bill@2004";

// URLs
const char* logServerURL = "http://iot_proj.springreen.in/log";
const char* gpsPostURL = "http://iot_proj.springreen.in/gps";
const char* websocketHost = "iot_proj.springreen.in";
const uint16_t websocketPort = 80;
const char* websocketPath = "/ws/bike-001";

// Hardware Pins
#define GREEN_LED 25
#define RED_LED 26
#define BUZZER 33
#define RELAY 27

WebSocketsClient webSocket;
unsigned long lastGPSPost = 0;
unsigned long gpsInterval = 5 * 60 * 1000;  // 5 minutes

void buzz(int times, int duration = 150) {
  for (int i = 0; i < times; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(duration);
    digitalWrite(BUZZER, LOW);
    delay(150);
  }
}

void sendLog(String level, String message) {
  Serial.printf("[%s] %s\n", level.c_str(), message.c_str());

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(logServerURL);
    http.addHeader("Content-Type", "application/json");

    String payload = "{";
    payload += "\"device\":\"bike_module\",";
    payload += "\"level\":\"" + level + "\",";
    payload += "\"message\":\"" + message + "\",";
    payload += "\"timestamp\":\"" + String(millis()) + "\"}";

    http.POST(payload);
    http.end();
  }
}

void postGPS() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient geo;
    geo.begin("http://ip-api.com/json/");
    int geoCode = geo.GET();

    if (geoCode == 200) {
      String response = geo.getString();
      geo.end();

      DynamicJsonDocument doc(512);
      DeserializationError error = deserializeJson(doc, response);

      if (!error) {
        float lat = doc["lat"];
        float lon = doc["lon"];

        // Now send this to your actual server
        HTTPClient http;
        http.begin(gpsPostURL);
        http.addHeader("Content-Type", "application/json");

        String payload = "{";
        payload += "\"uuid\":\"bike-001\",";
        payload += "\"lat\":" + String(lat, 6) + ",";
        payload += "\"lon\":" + String(lon, 6) + ",";
        payload += "\"timestamp\":\"" + String(millis()) + "\"}";

        http.POST(payload);
        http.end();

        sendLog("INFO", "GPS Data posted via ip-api");
      } else {
        sendLog("ERROR", "Failed to parse IP Geo data");
      }
    } else {
      geo.end();
      sendLog("ERROR", "Failed to get location from ip-api");
    }
  }
}

// WebSocket message handler
void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      sendLog("INFO", "WebSocket connected");
      break;

    case WStype_DISCONNECTED:
      sendLog("ERROR", "WebSocket disconnected");
      break;

    case WStype_TEXT:
      {
        String message = String((char*)payload);
        message.trim();
        sendLog("INFO", "Received from server: " + message);

        if (message == "302") {
          digitalWrite(RELAY, HIGH);  // Turn on bike
          digitalWrite(GREEN_LED, HIGH);
          digitalWrite(RED_LED, LOW);
          tone(BUZZER, 1000);
          delay(200);
          noTone(BUZZER);
          delay(100);
          tone(BUZZER, 1000);
          delay(200);
          noTone(BUZZER);
          sendLog("ACTION", "Start bike - Relay ON");

        } else if (message == "304") {
          digitalWrite(RELAY, LOW);  // Turn off bike
          digitalWrite(RED_LED, HIGH);
          digitalWrite(GREEN_LED, LOW);
          tone(BUZZER, 800);
          delay(300);
          noTone(BUZZER);
          sendLog("ACTION", "Stop bike - Relay OFF");

        } else if (message == "404") {
          digitalWrite(RELAY, LOW);  // Block ignition
          digitalWrite(RED_LED, HIGH);
          digitalWrite(GREEN_LED, HIGH);  // Yellow-like warning
          tone(BUZZER, 500);
          delay(500);
          noTone(BUZZER);
          sendLog("ACTION", "Override required - Halted");

        } else {
          digitalWrite(RELAY, LOW);  // Safe state
          digitalWrite(RED_LED, LOW);
          digitalWrite(GREEN_LED, LOW);
          noTone(BUZZER);
          sendLog("STATE", "Idle or unknown state - Relay OFF");
          // IDLE HERE NO NEED TO DO ANYTHING
        }

        break;
      }

    default:
      break;
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(RELAY, OUTPUT);

  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);
  digitalWrite(BUZZER, LOW);
  digitalWrite(RELAY, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  int attempts = 0;

  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    digitalWrite(GREEN_LED, HIGH);
    delay(200);
    digitalWrite(GREEN_LED, LOW);
    delay(200);
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(GREEN_LED, HIGH);
    sendLog("INFO", "WiFi connected");
  } else {
    digitalWrite(RED_LED, HIGH);
    sendLog("ERROR", "WiFi failed");
    return;
  }

  webSocket.begin(websocketHost, websocketPort, websocketPath);
  webSocket.onEvent(onWebSocketEvent);
  webSocket.setReconnectInterval(5000);
}

void loop() {
  webSocket.loop();

  // Periodic GPS Post
  if (millis() - lastGPSPost > gpsInterval) {
    postGPS();
    lastGPSPost = millis();
  }

  delay(10);
}
