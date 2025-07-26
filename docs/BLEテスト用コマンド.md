# BLEテスト用コマンド

## LightBlueでの正しい入力方法

### 方法1: Write Valueで直接入力

1. **キャラクタリスティックをタップ**
2. **「Write new value」をタップ**
3. **入力フィールドが表示されたら、以下のいずれかの方法で入力：**

#### Text入力（推奨）
- 入力タイプを「Text」または「ASCII」に変更
- 直接文字列を入力: `TEST`
- Sendボタンをタップ

#### Hex入力
以下の16進数値を入力（スペース区切り）：

**"TEST"を送信する場合:**
```
54 45 53 54
```

**"T50,P0,R0,Y0"を送信する場合:**
```
54 35 30 2C 50 30 2C 52 30 2C 59 30
```

### 方法2: nRF Connectを使用（推奨）

nRF Connectの方が確実にテキスト送信できます：

1. **App StoreからnRF Connectをインストール**
2. **アプリを開いてSCANタブで"RaspberryPiDrone"を探す**
3. **CONNECTをタップ**
4. **サービスを展開**
5. **書き込み用キャラクタリスティック（6E400002...）の上矢印をタップ**
6. **TEXTタブを選択**
7. **テキストボックスに`TEST`と入力**
8. **SENDをタップ**

## テスト用コマンド一覧

### 基本テスト
```
TEST
HELLO
123
```

### ドローン制御コマンド
```
T0
T50
T100
T50,P0,R0,Y0
T75,P10,R-5,Y20
STOP
STATUS
```

## 期待されるログ出力

### 成功時
```
Raw value type: <class 'dbus.Array'>, length: 4
Raw value bytes: ['0x54', '0x45', '0x53', '0x54']
Received BLE command: 'TEST'
Sent to Arduino via I2C: 'TEST'
```

### エラー時の対処

もしLightBlueで上手くいかない場合は、以下のアプリを試してください：

1. **Serial Bluetooth Terminal**
   - よりシンプルなテキスト送信インターフェース

2. **BLE Terminal HM-10**
   - UART風のインターフェースでテキスト送信に特化

3. **Bluefruit Connect by Adafruit**
   - UART機能でテキスト送信が簡単

## Pythonテストスクリプト（PC用）

PCからテストする場合は、以下のPythonスクリプトを使用できます：

```python
import asyncio
from bleak import BleakClient

DEVICE_ADDRESS = "XX:XX:XX:XX:XX:XX"  # Raspberry PiのMACアドレス
COMMAND_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

async def send_command():
    async with BleakClient(DEVICE_ADDRESS) as client:
        # テストコマンド送信
        await client.write_gatt_char(COMMAND_UUID, b"TEST")
        print("Sent: TEST")

asyncio.run(send_command())
```