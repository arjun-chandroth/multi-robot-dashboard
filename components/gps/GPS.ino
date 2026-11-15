#include <TinyGPS++.h>

TinyGPSPlus gps;

void setup() {
  Serial.begin(9600);       // For Serial Monitor
  Serial1.begin(9600);      // For GPS Module (TX from GPS → RX1 on Mega)
  Serial.println("GPS Module Test - Arduino Mega using Serial1");
}

void loop() {
  while (Serial1.available() > 0) {
    gps.encode(Serial1.read());

    if (gps.location.isUpdated()) {
      Serial.print("Latitude: ");
      Serial.println(gps.location.lat(), 6);

      Serial.print("Longitude: ");
      Serial.println(gps.location.lng(), 6);

      Serial.print("Altitude: ");
      Serial.print(gps.altitude.meters());
      Serial.println(" m");

      Serial.print("Satellites: ");
      Serial.println(gps.satellites.value());

      Serial.print("Speed: ");
      Serial.print(gps.speed.kmph());
      Serial.println(" km/h");

      Serial.print("Date: ");
      Serial.print(gps.date.day());
      Serial.print("/");
      Serial.print(gps.date.month());
      Serial.print("/");
      Serial.println(gps.date.year());

      Serial.print("Time (UTC): ");
      Serial.print(gps.time.hour());
      Serial.print(":");
      Serial.print(gps.time.minute());
      Serial.print(":");
      Serial.println(gps.time.second());

      Serial.println("--------------------------");
    }
  }
}
