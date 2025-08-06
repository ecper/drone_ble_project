#!/bin/bash

# Drone BLE Server auto startup settings script

echo "=== Drone BLE Server Auto Startup Settings ==="

# Confirm current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/drone-ble.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "error: drone-ble.service not found"
    exit 1
fi

echo "1. Copying systemd service file..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

echo "2. Reloading systemd..."
sudo systemctl daemon-reload

echo "3. Enabling service..."
sudo systemctl enable drone-ble.service

echo "4. Starting service..."
sudo systemctl start drone-ble.service

echo ""
echo "=== Settings Complete ==="
echo "Checking service state:"
sudo systemctl status drone-ble.service

echo ""
echo "=== Available Commands ==="
echo "Check status:         sudo systemctl status drone-ble.service"
echo "Check logs:           sudo journalctl -u drone-ble.service -f"
echo "Restart service:      sudo systemctl restart drone-ble.service"
echo "Stop service:         sudo systemctl stop drone-ble.service"
echo "Disable service:      sudo systemctl disable drone-ble.service"
echo ""
echo "Note: The service will automatically start on Raspberry Pi reboot."
