#!/bin/bash
# Bluetoothペアリング要求を無効化するセットアップスクリプト

echo "Bluetoothペアリング要求を無効化する設定を開始します..."

# 1. BlueZのメイン設定ファイルを編集
echo "BlueZ設定ファイルを更新中..."
sudo tee /etc/bluetooth/main.conf > /dev/null << 'EOF'
[General]
# デバイス名
Name = RaspberryPiDrone

# デバイスクラス（0x000000 = 未分類デバイス）
Class = 0x000000

# ペアリングモード設定
# NoInputNoOutput = ペアリング時の確認を要求しない
PairableTimeout = 0
DiscoverableTimeout = 0

[Policy]
# 自動信頼設定
AutoEnable=true

[GATT]
# GATT/ATTのチャンネル設定
Channels = 1
EOF

# 2. bluetoothサービスの設定を更新
echo "Bluetoothサービス設定を更新中..."
sudo mkdir -p /etc/systemd/system/bluetooth.service.d/
sudo tee /etc/systemd/system/bluetooth.service.d/override.conf > /dev/null << 'EOF'
[Service]
ExecStart=
ExecStart=/usr/lib/bluetooth/bluetoothd --noplugin=sap --compat --nodetach
ExecStartPost=/usr/bin/sdptool add SP
EOF

# 3. 自動ペアリング承認スクリプトを作成
echo "自動ペアリング承認スクリプトを作成中..."
sudo tee /usr/local/bin/bluetooth-agent.py > /dev/null << 'EOF'
#!/usr/bin/env python3
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = "/test/agent"

class Agent(dbus.service.Object):
    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print(f"AuthorizeService: {device} {uuid}")
        return

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print(f"RequestPinCode: {device}")
        return "0000"

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print(f"RequestPasskey: {device}")
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print(f"RequestConfirmation: {device} {passkey}")
        return

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print(f"RequestAuthorization: {device}")
        return

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    
    agent = Agent(bus, AGENT_PATH)
    
    obj = bus.get_object("org.bluez", "/org/bluez")
    manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
    manager.RequestDefaultAgent(AGENT_PATH)
    
    print("Bluetooth agent running...")
    mainloop = GLib.MainLoop()
    mainloop.run()
EOF

sudo chmod +x /usr/local/bin/bluetooth-agent.py

# 4. 自動起動サービスを作成
echo "自動起動サービスを作成中..."
sudo tee /etc/systemd/system/bluetooth-agent.service > /dev/null << 'EOF'
[Unit]
Description=Bluetooth Agent for automatic pairing
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/local/bin/bluetooth-agent.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. デバイスを信頼済みリストに追加するスクリプト
echo "デバイス自動信頼スクリプトを作成中..."
sudo tee /usr/local/bin/trust-all-devices.sh > /dev/null << 'EOF'
#!/bin/bash
# 接続したデバイスを自動的に信頼する
bluetoothctl << COMMANDS
discoverable on
pairable on
agent NoInputNoOutput
default-agent
COMMANDS
EOF

sudo chmod +x /usr/local/bin/trust-all-devices.sh

# 6. サービスの再起動と有効化
echo "サービスを再起動中..."
sudo systemctl daemon-reload
sudo systemctl restart bluetooth
sudo systemctl enable bluetooth-agent.service
sudo systemctl start bluetooth-agent.service

# 7. 現在の設定を適用
echo "現在の設定を適用中..."
sudo /usr/local/bin/trust-all-devices.sh

echo "設定完了！"
echo ""
echo "確認コマンド:"
echo "  sudo systemctl status bluetooth-agent"
echo "  bluetoothctl show"
echo ""
echo "注意: drone_ble_server.pyを再起動してください。"