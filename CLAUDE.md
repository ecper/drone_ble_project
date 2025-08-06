# CLAUDE.md

This file provides guidance for Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a development project for a custom drone control system. The system consists of three main components:

1. **iPhone App** (React Native Expo): User interface, BLE communication
2. **Raspberry Pi 5**: BLE server, main controller, I2C master
3. **Arduino**: Low-level control, motor/ESC control, sensor data collection

### Communication Flow
- iPhone → Raspberry Pi: BLE (Bluetooth Low Energy)
- Raspberry Pi → Arduino: I2C (Inter-Integrated Circuit)
- Arduino → Motors: PWM (Pulse Width Modulation)

## Current Project Status

- **Implemented**: BLE server for Raspberry Pi (`drone_ble_server.py`)
- **Not Implemented**: 
  - iPhone app (React Native Expo)
  - Arduino sketch
  - ESC/motor control logic

## System Architecture

### 1. Raspberry Pi Side (drone_ble_server.py)

**BLE Server Features**
- Uses D-Bus and BlueZ API
- GATT server implementation
- BLE advertising (device name: "RaspberryPiDrone")

**GATT Service Structure**
- Service UUID: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
- Command characteristic: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (write, write-without-response)
- Status characteristic: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (read, notify)

**I2C Configuration**
- Bus: 1 (standard for Raspberry Pi 4/5)
- Arduino address: 0x08
- Uses smbus2 library

### 2. iPhone App Side (Not Implemented)

**Technology Stack**
- React Native Expo
- react-native-ble-plx library
- Expo Dev Client (does not work with Expo Go)

**Main Features**
- BLE scan and device connection
- Joystick UI operation
- Command transmission (example: "T1500,P10,R20,Y-5")
- Status reception and display

### 3. Arduino Side (Not Implemented)

**Main Features**
- Operates as I2C slave
- Motor/ESC control (PWM signals)
- Sensor data collection (IMU, etc.)
- Flight stabilization with PID control

## Development Commands

### Server Execution
```bash
# Run with Python 3
python3 drone_ble_server.py

# Use sudo if permission error occurs
sudo python3 drone_ble_server.py
```

### System Requirements
```bash
# Enable I2C interface
sudo raspi-config
# Navigate to Interface Options → I2C → Enable

# Install required system packages
sudo apt-get install bluez python3-dbus python3-gi

# Install Python dependencies
pip3 install smbus2
```

### Debugging
```bash
# Check Bluetooth service status
systemctl status bluetooth

# Monitor running system logs
journalctl -f | grep -i bluetooth

# Check I2C devices
i2cdetect -y 1

# Test BLE advertising
sudo hcitool lescan
```

## Code Structure

### Main Classes
- `Application`: D-Bus object that manages GATT services
- `DroneService`: Custom GATT service for drone control
- `CommandCharacteristic`: Processes write operations from iPhone
- `StatusCharacteristic`: Processes read/notification operations to iPhone
- `Advertisement`: Manages BLE advertising

### Main Functions
- `main()`: Entry point, initializes I2C and D-Bus, starts services
- `send_status_notification()`: Sends BLE notifications to connected devices
- `arduino_reader_loop()`: Regular I2C polling (currently uses dummy data)
- `check_system_requirements()`: Verifies system configuration

### Error Handling
- I2C communication errors are caught and logged
- BLE registration failures trigger application termination
- Status notifications include error codes (example: "ERR:I2C_Not_Ready")

## Development Phases

### Phase 1: Raspberry Pi BLE & I2C Environment Setup and Testing
- Update Raspberry Pi OS and enable I2C
- Set up Python environment and verify drone_ble_server.py operation
- Basic implementation and testing of Arduino I2C slave

### Phase 2: iPhone App Development and Integration Testing
- React Native Expo project setup
- BLE client functionality implementation
- Communication testing with Raspberry Pi

### Phase 3: Drone Control Logic Implementation
- Arduino flight controller implementation
- PID control and motor control
- Safety testing and adjustments

## Important Notes

1. **Development Environment**: drone_ble_server.py runs on Raspberry Pi and should not be executed on development PC

2. **I2C Communication**: 
   - arduino_reader_loop currently generates dummy data
   - Logic level converter needed between Raspberry Pi (3.3V) and Arduino (5V)

3. **Permissions**: sudo required for BLE operations on Raspberry Pi

4. **UUID**: Current UUIDs are examples and should be replaced with custom-generated UUIDs in production environment

5. **Hardware**:
   - Motors: MT2204-2300KV brushless DC motors
   - ESC (Electronic Speed Controller) required
   - IMU and other sensors required

## Project Structure (Recommended)

```
drone_ble_project/
├── raspberry_pi/
│   └── drone_ble_server.py    # Implemented
├── arduino/
│   └── drone_controller/      # Not implemented
│       └── drone_controller.ino
├── iphone_app/                # Not implemented
│   ├── package.json
│   ├── app.json
│   └── src/
│       └── App.js
└── docs/
    └── design_document.md