# Multi-Robot Dashboard

This project starts with the try3 Arduino Mega rover firmware and a standalone
GPS module test. Later commits add each available saved project snapshot in
ascending try-number order. Gaps in the sequence reflect snapshots that were
not available.

## try3 firmware

The sketch drives motors and reports readings from environmental, motion, and
impact sensors over serial. It targets an Arduino Mega-class board and uses the
DHT sensor library, Adafruit Unified Sensor, and Adafruit ADXL345 libraries.

Open `try3.ino` in the Arduino IDE, select the board and serial port, and upload
it. The serial interface uses 115200 baud. Commands are `F` (forward), `B`
(backward), `L` (left), `R` (right), `S` (stop), `D` (telemetry), `X` (reset
counters), and `O` (toggle the obstacle-mode state flag).
