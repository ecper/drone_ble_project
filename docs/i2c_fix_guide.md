# I2C通信エラー解決ガイド

## エラー内容
`[Errno 11] Resource temporarily unavailable` - I2Cデバイスが一時的に利用できない

## 考えられる原因

1. **Arduinoが接続されていない、または電源が入っていない**
2. **I2Cアドレスの不一致**
3. **配線の問題**
4. **プルアップ抵抗の不足**
5. **文字列が長すぎる**

## 解決方法

### 1. I2Cデバイスの確認
```bash
# I2Cデバイスをスキャン
sudo i2cdetect -y 1
```
- Arduinoのアドレス（0x08）が表示されるか確認

### 2. 配線の確認
- Raspberry Pi → Arduino
  - GPIO 2 (SDA) → Arduino SDA
  - GPIO 3 (SCL) → Arduino SCL
  - GND → GND
  - 3.3V → 5V (レベルシフタ経由推奨)

### 3. コード修正案

#### 方法1: 文字列を小さなチャンクに分割
```python
def write_i2c_string(address, string, chunk_size=16):
    """文字列を小さなチャンクに分けて送信"""
    try:
        for i in range(0, len(string), chunk_size):
            chunk = string[i:i+chunk_size]
            data_bytes = [ord(char) for char in chunk]
            bus.write_i2c_block_data(address, i, data_bytes)
            time.sleep(0.01)  # 10ms待機
    except Exception as e:
        logger.error(f"I2C write error: {e}")
```

#### 方法2: 単一バイトずつ送信
```python
def write_i2c_bytes(address, string):
    """1バイトずつ送信"""
    try:
        for i, char in enumerate(string):
            bus.write_byte_data(address, i, ord(char))
            time.sleep(0.001)  # 1ms待機
    except Exception as e:
        logger.error(f"I2C write error: {e}")
```

#### 方法3: SMBusメッセージを使用
```python
from smbus2 import SMBus, i2c_msg

def write_i2c_message(address, string):
    """i2c_msgを使用して送信"""
    try:
        msg = i2c_msg.write(address, string.encode())
        bus.i2c_rdwr(msg)
    except Exception as e:
        logger.error(f"I2C write error: {e}")
```

### 4. Arduino側の対策

```cpp
// Arduino側のI2C受信コード例
#include <Wire.h>

#define I2C_ADDRESS 0x08
char i2c_buffer[32];
volatile bool new_data = false;

void setup() {
  Wire.begin(I2C_ADDRESS);
  Wire.onReceive(receiveEvent);
  Serial.begin(115200);
}

void receiveEvent(int bytes) {
  int i = 0;
  while (Wire.available() && i < sizeof(i2c_buffer)-1) {
    i2c_buffer[i++] = Wire.read();
  }
  i2c_buffer[i] = '\0';
  new_data = true;
}

void loop() {
  if (new_data) {
    Serial.print("Received: ");
    Serial.println(i2c_buffer);
    new_data = false;
  }
}
```

### 5. テスト手順

1. まず簡単なテストから始める
```bash
# Python3で直接テスト
python3
>>> import smbus2
>>> bus = smbus2.SMBus(1)
>>> bus.write_byte(0x08, 65)  # 'A'を送信
```

2. エラーが出る場合は、I2Cの速度を下げる
```bash
# /boot/config.txt に追加
dtparam=i2c_baudrate=10000  # 10kHzに下げる
```

3. 再起動後、再度テスト

### 6. 推奨される実装

エラーハンドリングを強化した実装：
```python
def send_i2c_command(command_str, max_retries=3):
    """リトライ機能付きI2C送信"""
    for attempt in range(max_retries):
        try:
            # 短いコマンドは直接送信
            if len(command_str) <= 16:
                data_bytes = [ord(char) for char in command_str]
                bus.write_i2c_block_data(ARDUINO_I2C_ADDRESS, 0, data_bytes)
            else:
                # 長いコマンドは分割送信
                for i in range(0, len(command_str), 16):
                    chunk = command_str[i:i+16]
                    data_bytes = [ord(char) for char in chunk]
                    bus.write_i2c_block_data(ARDUINO_I2C_ADDRESS, i//16, data_bytes)
                    time.sleep(0.01)
            
            logger.info(f"I2C送信成功: {command_str}")
            return True
            
        except OSError as e:
            if e.errno == 11:  # Resource temporarily unavailable
                logger.warning(f"I2Cバスビジー、リトライ {attempt+1}/{max_retries}")
                time.sleep(0.1)
            else:
                logger.error(f"I2Cエラー: {e}")
                return False
    
    return False
```