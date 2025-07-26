#!/bin/bash
# 強制的にペアリングを無効化

echo "強制的にペアリング無効化設定..."

# Bluetoothを一時停止
sudo systemctl stop bluetooth

# btmgmtコマンドで直接設定
sudo btmgmt -i hci0 power off
sudo btmgmt -i hci0 bredr off    # Classic Bluetoothを無効化
sudo btmgmt -i hci0 le on        # BLE only
sudo btmgmt -i hci0 bondable off # ボンディング無効
sudo btmgmt -i hci0 pairable off # ペアリング無効
sudo btmgmt -i hci0 privacy off  # プライバシー無効
sudo btmgmt -i hci0 sc off       # Secure Connections無効
sudo btmgmt -i hci0 ssp off      # Simple Secure Pairing無効
sudo btmgmt -i hci0 power on

# hciconfigで追加設定
sudo hciconfig hci0 leadv 3      # BLEアドバタイジング（接続可能・非指向性）

# Bluetoothサービスを再開
sudo systemctl start bluetooth

echo "完了！"