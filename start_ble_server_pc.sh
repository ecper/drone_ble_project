#!/bin/bash
# PC環境でBLEサーバーを起動するスクリプト

echo "=== PC環境でBLEサーバーを起動 ==="

# 依存関係の確認
echo "依存関係を確認中..."
python3 -c "
try:
    import dbus, gi
    from gi.repository import GLib
    print('✅ 必要な依存関係が揃っています')
except ImportError as e:
    print('❌ 依存関係が不足しています:', e)
    print('以下のコマンドで依存関係をインストールしてください:')
    print('./install_pc_ble_deps.sh')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "依存関係のインストールが必要です"
    exit 1
fi

# Bluetoothサービスの確認
echo "Bluetoothサービスを確認中..."
if ! systemctl is-active --quiet bluetooth; then
    echo "Bluetoothサービスを開始中..."
    sudo systemctl start bluetooth
fi

# BluetoothアダプターがPowerOnになっているか確認
echo "Bluetoothアダプターの状態を確認中..."
bluetoothctl show | grep "Powered: yes" > /dev/null
if [ $? -ne 0 ]; then
    echo "Bluetoothアダプターを有効化中..."
    echo "power on" | bluetoothctl
    sleep 2
fi

# 権限確認
echo "権限を確認中..."
if ! id -nG "$USER" | grep -qw "bluetooth"; then
    echo "警告: ユーザーがbluetoothグループに属していません"
    echo "以下のコマンドを実行してログアウト・ログインしてください:"
    echo "sudo usermod -a -G bluetooth $USER"
fi

# BLEサーバーを起動
echo "BLEサーバーを起動中..."
cd "$(dirname "$0")"
echo "使用するPython: $(which python3)"

# pyenv環境の場合、システムPythonを使用
if command -v pyenv >/dev/null 2>&1; then
    echo "pyenv環境を検出しました。システムPythonを使用します。"
    /usr/bin/python3 rasberry_pi/drone_ble_server.py
else
    python3 rasberry_pi/drone_ble_server.py
fi