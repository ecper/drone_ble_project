# BLEサービスデバッグガイド

## 問題の状況
- PC側からRaspberry Piに接続はできる
- しかし、GATTサービスが見つからない（サービス数: 0）
- Raspberry Pi側のログでは正常に登録されている

## デバッグ手順

### 1. Raspberry Pi側の確認

#### bluetoothctlでサービスを確認
```bash
# Raspberry Piで実行
sudo bluetoothctl

# bluetoothctl内で
info D8:3A:DD:EE:48:0D
# UUIDsの項目に 6e400001-b5a3-f393-e0a9-e50e24dcca9e があるか確認

# GATTサービスを確認
menu gatt
list-attributes D8:3A:DD:EE:48:0D
```

#### D-Bus経由でサービスを確認
```bash
# Raspberry Piで実行
sudo dbus-send --system --print-reply --dest=org.bluez /org/bluez/hci0 org.freedesktop.DBus.ObjectManager.GetManagedObjects | grep -A 20 "6e400001"
```

### 2. PC側での確認

#### bluetoothctlを使った手動接続
```bash
# PC側で実行
sudo bluetoothctl

# bluetoothctl内で
scan on
# Raspberry Piが見つかったら
connect D8:3A:DD:EE:48:0D

# 接続後
info D8:3A:DD:EE:48:0D
menu gatt
list-attributes D8:3A:DD:EE:48:0D
```

#### gatttoolを使った確認（非推奨だが有効）
```bash
# PC側で実行
sudo gatttool -b D8:3A:DD:EE:48:0D -I

# gatttool内で
connect
primary
characteristics
```

### 3. シンプルなテストスクリプト実行
```bash
# 作成したテストスクリプトを実行
python3 test_simple_connection.py
```

### 4. 考えられる原因と対策

#### 原因1: ペアリングの問題
既にペアリングされているデバイスの場合、サービスが正しく表示されないことがある。

**対策:**
```bash
# PC側で
bluetoothctl
remove D8:3A:DD:EE:48:0D
exit

# Raspberry Pi側で
bluetoothctl
remove [PC_MAC_ADDRESS]
exit
```

#### 原因2: キャッシュの問題
BlueZがサービス情報をキャッシュしている可能性。

**対策:**
```bash
# PC側で
sudo systemctl restart bluetooth

# または、キャッシュをクリア
sudo rm -rf /var/lib/bluetooth/*/cache/*
```

#### 原因3: 権限の問題
BLEアクセスに必要な権限が不足している可能性。

**対策:**
```bash
# PC側で
# ユーザーをbluetoothグループに追加
sudo usermod -a -G bluetooth $USER
# ログアウトして再ログイン

# または、sudoで実行
sudo python3 drone_controller_v3.py
```

#### 原因4: Raspberry Pi側のGATT登録の問題
サービスが正しく登録されていない可能性。

**対策:**
Raspberry Pi側のdrone_ble_server.pyに以下の確認コードを追加：
```python
# RegisterApplicationの後に追加
time.sleep(2)
objects = app.GetManagedObjects()
for path, interfaces in objects.items():
    if GATT_SERVICE_IFACE in interfaces:
        print(f"Registered service at: {path}")
        print(f"UUID: {interfaces[GATT_SERVICE_IFACE]['UUID']}")
```

### 5. 代替案: シンプルなBLEサーバーでテスト

最小限のBLEサーバーを作成してテスト：
```python
# Raspberry Piで minimal_ble_server.py として保存
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

class TestService(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        dbus.service.Object.__init__(self, bus, self.path)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        response[self.path] = {
            GATT_SERVICE_IFACE: {
                'UUID': '12345678-1234-5678-1234-56789abcdef0',
                'Primary': True,
                'Characteristics': dbus.Array([], signature='o')
            }
        }
        return response

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    
    service = TestService(bus, 0)
    
    manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, '/org/bluez/hci0'),
        GATT_MANAGER_IFACE
    )
    
    manager.RegisterApplication(service.path, {},
                                reply_handler=lambda: print("App registered"),
                                error_handler=lambda error: print(f"Failed: {error}"))
    
    mainloop = GLib.MainLoop()
    mainloop.run()

if __name__ == '__main__':
    main()
```

このシンプルなサーバーで接続できるか確認してください。