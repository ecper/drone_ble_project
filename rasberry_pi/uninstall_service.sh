#!/bin/bash

# Drone BLE Server auto startup disable script

echo "=== Drone BLE Server Auto Startup Disable ==="

echo "1. Stopping service..."
sudo systemctl stop drone-ble.service

echo "2. Disabling service..."
sudo systemctl disable drone-ble.service

echo "3. Deleting systemd service file..."
sudo rm -f /etc/systemd/system/drone-ble.service

echo "4. Reloading systemd..."
sudo systemctl daemon-reload

echo ""
echo "=== Disable Complete ==="
echo "Auto startup of drone_ble_server.py has been disabled."
echo ""
echo "To start manually:"
echo "cd /home/uchida/Documents/fov-prog/drone_ble_project/raspberry_pi"
echo "sudo python3 drone_ble_server.py"
