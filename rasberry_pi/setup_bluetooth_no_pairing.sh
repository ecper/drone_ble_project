#!/bin/bash
# シンプルなペアリング無効化設定

echo "Bluetoothをペアリング不要で設定中..."

# Bluetoothサービスが正常に動作していることを確認
sudo systemctl restart bluetooth
sleep 2

# bluetoothctlで基本設定
bluetoothctl << EOF
power on
agent NoInputNoOutput
default-agent
pairable on
discoverable on
exit
EOF

echo "設定完了！"
echo ""
echo "この設定により："
echo "1. BLE接続時にペアリング確認が不要になります"
echo "2. iPhoneから直接接続できます"
echo ""
echo "drone_ble_server.pyを起動してください："
echo "sudo python3 drone_ble_server.py"