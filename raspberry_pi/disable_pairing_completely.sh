#!/bin/bash
# Raspberry PiでBLEペアリングを完全に無効化するスクリプト

echo "=== BLEペアリングを完全に無効化 ==="

# 1. 既存の設定とペアリング情報を完全にクリア
echo "1. 既存の設定をクリア..."
sudo systemctl stop bluetooth
sudo rm -rf /var/lib/bluetooth/*
sudo rm -rf /etc/bluetooth/main.conf.d/*

# 2. BlueZのメイン設定を更新（ペアリング無効化）
echo "2. BlueZ設定を更新..."
sudo mkdir -p /etc/bluetooth/main.conf.d/
sudo tee /etc/bluetooth/main.conf > /dev/null << 'EOF'
[General]
# デバイス名
Name = RaspberryPiDrone

# ペアリングを無効化
PairableTimeout = 0
Pairable = false

# 常に検出可能
DiscoverableTimeout = 0
Discoverable = true

# Just Worksペアリングモード（確認不要）
JustWorksRepairing = always

# クラスをBLEペリフェラルに設定
Class = 0x000000

# デバイスIDを無効化
DeviceID = false

[Policy]
# 自動的にサービスを有効化
AutoEnable = true

[GATT]
# キャッシュを無効化（ペアリング不要）
Cache = no

# 暗号化キーサイズを0（暗号化不要）
KeySize = 0

[LE]
# BLEのセキュリティモード1レベル1（セキュリティなし）
# 広告間隔を短く
MinAdvertisementInterval = 100
MaxAdvertisementInterval = 150
EOF

# 3. systemdサービスの設定を更新
echo "3. Bluetoothサービス設定を更新..."
sudo mkdir -p /etc/systemd/system/bluetooth.service.d/
sudo tee /etc/systemd/system/bluetooth.service.d/no-pairing.conf > /dev/null << 'EOF'
[Service]
ExecStart=
ExecStart=/usr/lib/bluetooth/bluetoothd -C -P sap,input,avrcp
EOF

# 4. D-Bus設定を更新（全権限許可）
echo "4. D-Bus権限設定..."
sudo tee /etc/dbus-1/system.d/bluetooth-no-pairing.conf > /dev/null << 'EOF'
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy context="default">
    <allow own="org.bluez"/>
    <allow send_destination="org.bluez"/>
    <allow send_interface="org.bluez.GattService1"/>
    <allow send_interface="org.bluez.GattCharacteristic1"/>
    <allow send_interface="org.bluez.GattDescriptor1"/>
    <allow send_interface="org.bluez.LEAdvertisement1"/>
    <allow send_interface="org.freedesktop.DBus.Properties"/>
    <allow send_interface="org.freedesktop.DBus.ObjectManager"/>
    <allow send_interface="org.freedesktop.DBus.Introspectable"/>
  </policy>
</busconfig>
EOF

# 5. hcitoolで低レベル設定
echo "5. HCI設定を適用..."
sudo systemctl daemon-reload
sudo systemctl restart dbus
sudo systemctl restart bluetooth
sleep 3

# Bluetoothアダプターを設定
sudo hciconfig hci0 up
sudo hciconfig hci0 noscan
sudo hciconfig hci0 sspmode 0  # Simple Secure Pairingを無効化
sudo hciconfig hci0 noauth     # 認証不要
sudo hciconfig hci0 noencrypt  # 暗号化不要

# 6. bluetoothctlで最終設定
echo "6. bluetoothctl設定..."
sudo bluetoothctl << EOF
power on
agent NoInputNoOutput
default-agent
pairable off
discoverable on
show
quit
EOF

# 7. BLEセキュリティレベルを最低に設定
echo "7. BLEセキュリティ設定..."
sudo btmgmt le on
sudo btmgmt bondable off
sudo btmgmt pairable off
sudo btmgmt connectable on
sudo btmgmt advertising on

echo ""
echo "=== 設定完了 ==="
echo "ペアリング要求は完全に無効化されました。"
echo ""
echo "確認方法："
echo "  sudo hciconfig -a"
echo "  sudo bluetoothctl show"
echo ""
echo "drone_ble_server.pyを起動してください："
echo "  sudo python3 drone_ble_server.py"