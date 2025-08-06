#!/bin/bash
# PC環境でBLEサーバーを動作させるための依存関係インストールスクリプト

echo "PC環境用BLE依存関係のインストールを開始します..."

# システムの更新
echo "システムを更新中..."
sudo apt update

# BlueZ（Bluetoothスタック）のインストール
echo "BlueZ関連パッケージをインストール中..."
sudo apt install -y bluez bluez-tools

# GObjectライブラリとPython3-gi
echo "GObject関連パッケージをインストール中..."
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0

# GLib開発用パッケージ
echo "GLib開発パッケージをインストール中..."
sudo apt install -y libglib2.0-dev libgirepository1.0-dev

# D-Bus関連パッケージ
echo "D-Bus関連パッケージをインストール中..."
sudo apt install -y python3-dbus

# システムライブラリ
echo "システムライブラリをインストール中..."
sudo apt install -y libcairo2-dev pkg-config python3-dev

# pipで追加のPythonパッケージ
echo "追加のPythonパッケージをインストール中..."
pip3 install --user PyGObject dbus-python

# I2C関連（PCでは使用しないが、互換性のため）
echo "I2C関連パッケージをインストール中..."
pip3 install --user smbus2

# Bluetoothサービスの確認と開始
echo "Bluetoothサービスを確認中..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# 権限設定
echo "ユーザー権限を設定中..."
sudo usermod -a -G bluetooth $USER

echo ""
echo "インストールが完了しました！"
echo ""
echo "注意事項："
echo "1. ログアウト・ログインが必要な場合があります"
echo "2. BluetoothアダプターがPCに接続されていることを確認してください"
echo "3. 一部のLinuxディストリビューションでは追加設定が必要な場合があります"
echo ""
echo "テスト方法："
echo "python3 /path/to/drone_ble_server.py"