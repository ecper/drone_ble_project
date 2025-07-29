#!/bin/bash

# Drone BLE Server 自動起動解除スクリプト

echo "=== Drone BLE Server 自動起動解除 ==="

echo "1. サービスを停止中..."
sudo systemctl stop drone-ble.service

echo "2. サービスを無効化中..."
sudo systemctl disable drone-ble.service

echo "3. systemdサービスファイルを削除中..."
sudo rm -f /etc/systemd/system/drone-ble.service

echo "4. systemdを再読み込み中..."
sudo systemctl daemon-reload

echo ""
echo "=== 解除完了 ==="
echo "drone_ble_server.pyの自動起動が無効になりました"
echo ""
echo "手動起動する場合:"
echo "cd /home/uchida/Documents/fov-prog/drone_ble_project/raspberry_pi"
echo "sudo python3 drone_ble_server.py"