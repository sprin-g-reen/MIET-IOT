#include <WiFi.h>
#include <HTTPClient.h>

// Pin Definitions
#define TRIG_PIN 27
#define ECHO_PIN 14
#define MQ3_PIN 34
#define GREEN_LED 25
#define RED_LED 26
#define BUZZER 33

// WiFi Credentials
const char* ssid = "Airtel_Springreen";
const char* password = "Bill@2004";

// URLs
const char* LOG_URL = "http://iot_proj.springreen.in/PostLogs";
const char* DRUNKEN_API = "http://iot_proj.springreen.in/drunken";
const char* NOT_DRUNKEN_API = "http://iot_proj.springreen.in/not_drunken?uuid=helmet-001";

// Threshold
#define ALCOHOL_THRESHOLD 2450

void setup() {
  Serial.begin(115200);
  
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(MQ3_PIN, INPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();  // Reconnect if dropped
  }

  // Wait until helmet is worn
  while (!isHelmetWorn()) {
    redHelmetReadyFeedback();
    logAndPrint("INFO", "Helmet is not worn. Waiting...");
    delay(8000);
  }

  // HELMET WORN — Begin detection sequence
  logAndPrint("INFO", "Helmet worn. Starting alcohol check...");
  delay(1000); // Optional pause for stabilization

  int mq3Value = analogRead(MQ3_PIN);
  Serial.println("MQ3 Reading: " + String(mq3Value));

  if (mq3Value > ALCOHOL_THRESHOLD) {
    sendDrunkenAPI(mq3Value);
    logAndPrint("ALERT", "Drunken State Detected: " + String(mq3Value));
    drunkFeedback();
  } else {
    sendNotDrunkenAPI();
    logAndPrint("INFO", "Not Drunk State Detected: " + String(mq3Value));
    notDrunkFeedback();
  }

  // Stay in WAIT mode as long as helmet is worn
  logAndPrint("INFO", "Holding state until helmet is removed...");
  while (isHelmetWorn()) {
    delay(500); // Passive wait
  }

  // Helmet removed — Reset state
  digitalWrite(RED_LED, LOW);
  digitalWrite(GREEN_LED, LOW);
  logAndPrint("INFO", "Helmet removed. Returning to idle...");
  delay(1000); // Debounce time before restarting cycle
}

// ======================
// WiFi Logic
// ======================

void connectWiFi() {
  WiFi.begin(ssid, password);
  delay(2000);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 5) {
    attempts++;
    wifiFailureFeedback();
    logAndPrint("ERROR", "WiFi attempt " + String(attempts) + " failed.");
    delay(2000);
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiSuccessFeedback();
    logAndPrint("INFO", "WiFi Connected: " + WiFi.localIP().toString());
  }
}

// ======================
// Feedback Patterns
// ======================

void wifiFailureFeedback() {
  for (int i = 0; i < 2; i++) {
    digitalWrite(RED_LED, HIGH); buzzOnce(); delay(200);
    digitalWrite(RED_LED, LOW); delay(200);
  }
}

void wifiSuccessFeedback() {
  for (int i = 0; i < 2; i++) {
    digitalWrite(GREEN_LED, HIGH); buzzOnce(); delay(200);
    digitalWrite(GREEN_LED, LOW); delay(200);
  }
}

void redHelmetReadyFeedback() {
  digitalWrite(RED_LED, HIGH);
  buzzOnce();
}

void notDrunkFeedback() {
  digitalWrite(RED_LED, LOW);
  digitalWrite(GREEN_LED, HIGH);
  buzzThrice();
  Serial.println("NOT DRUNK - Green ON, Red OFF");
}

void drunkFeedback() {
  for (int i = 0; i < 5; i++) {
    digitalWrite(RED_LED, HIGH); delay(150);
    digitalWrite(RED_LED, LOW); delay(150);
  }
  digitalWrite(RED_LED, HIGH);
  buzzFourTimes();
  Serial.println("DRUNK - Red SIREN & Buzz 4x");
}

// ======================
// Utility Functions
// ======================

bool isHelmetWorn() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 20000); // 20ms timeout
  float distance = duration * 0.034 / 2.0;
  return distance < 8.0;
}

void buzzOnce() {
  digitalWrite(BUZZER, HIGH); delay(150); digitalWrite(BUZZER, LOW);
}

void buzzThrice() {
  for (int i = 0; i < 3; i++) {
    buzzOnce(); delay(150);
  }
}

void buzzFourTimes() {
  for (int i = 0; i < 4; i++) {
    buzzOnce(); delay(150);
  }
}

// ======================
// API Functions
// ======================

void sendDrunkenAPI(int mq3val) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(DRUNKEN_API);
  http.addHeader("Content-Type", "application/json");

  String body = "{\"uuid\":\"helmet-001\",\"alcohol_level\":" + String(mq3val) + ",\"timestamp\":\"" + String(millis()) + "\"}";
  int code = http.POST(body);
  Serial.println("DRUNKEN API Response: " + String(code));
  http.end();
}

void sendNotDrunkenAPI() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(NOT_DRUNKEN_API);
  int code = http.GET();
  Serial.println("NOT DRUNKEN API Response: " + String(code));
  http.end();
}

void logAndPrint(String level, String message) {
  Serial.println("[" + level + "] " + message);
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(LOG_URL);
  http.addHeader("Content-Type", "application/json");

  String payload = "{\"device\":\"helmet_module\",\"level\":\"" + level + "\",\"message\":\"" + message + "\",\"timestamp\":\"" + String(millis()) + "\"}";
  http.POST(payload);
  http.end();
}
