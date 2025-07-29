#!/bin/bash

# Drone BLE Server 自動起動設定スクリプト

echo "=== Drone BLE Server 自動起動設定 ==="

# 現在のディレクトリを確認
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/drone-ble.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "エラー: drone-ble.service が見つかりません"
    exit 1
fi

echo "1. systemdサービスファイルをコピー中..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

echo "2. systemdを再読み込み中..."
sudo systemctl daemon-reload

echo "3. サービスを有効化中..."
sudo systemctl enable drone-ble.service

echo "4. サービスを開始中..."
sudo systemctl start drone-ble.service

echo ""
echo "=== 設定完了 ==="
echo "サービス状態を確認:"
sudo systemctl status drone-ble.service

echo ""
echo "=== 使用可能なコマンド ==="
echo "状態確認:     sudo systemctl status drone-ble.service"
echo "ログ確認:     sudo journalctl -u drone-ble.service -f"
echo "再起動:       sudo systemctl restart drone-ble.service"
echo "停止:         sudo systemctl stop drone-ble.service"
echo "無効化:       sudo systemctl disable drone-ble.service"
echo ""
echo "注意: Raspberry Pi再起動後も自動で起動します"