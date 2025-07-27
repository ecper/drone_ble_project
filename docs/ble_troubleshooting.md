# BLE接続トラブルシューティングガイド

## 問題の概要
PC（Linux）からRaspberry PiのBLEサーバーに接続できるが、GATTサービスが見つからない。

## 確認手順

### 1. Raspberry Pi側の確認

#### BLEサーバーの状態確認
```bash
# Bluetoothサービスの状態
sudo systemctl status bluetooth

# BLEサーバーの実行
sudo python3 drone_ble_server.py
```

#### BLEアドバタイジングの確認
```bash
# 別のターミナルで実行
sudo hcitool lescan
```

### 2. PC側でのスキャン

#### 詳細スキャンツールの実行
```bash
# 作成したスキャナーを実行
python3 ble_scanner.py
```

このツールは以下を表示します：
- 検出されたすべてのBLEデバイス
- ターゲットデバイスのサービス一覧
- 各サービスの特性（Characteristic）
- 読み取り可能な値

### 3. 一般的な問題と解決策

#### 問題1: サービスが見つからない
**症状**: 接続はできるがGATTサービスが0個

**考えられる原因**:
1. Raspberry Pi側でサービスが正しく登録されていない
2. BlueZのバージョン互換性の問題
3. D-Bus権限の問題

**解決策**:
```bash
# Raspberry Pi側で実行
# BlueZのバージョン確認
bluetoothctl --version

# D-Busの再起動
sudo systemctl restart dbus

# Bluetoothアダプタのリセット
sudo hciconfig hci0 down
sudo hciconfig hci0 up
```

#### 問題2: UUIDの大文字小文字の問題
**症状**: サービスは見つかるがUUIDが一致しない

**解決策**:
- PC側のコードでUUIDを小文字に統一
- Raspberry Pi側でもUUIDを確認

#### 問題3: ペアリングの問題
**症状**: 接続時にペアリング要求が表示される

**解決策**:
```bash
# Raspberry Pi側で実行
# 既存のペアリング情報を削除
bluetoothctl
> remove [PC_MAC_ADDRESS]
> exit

# PC側で実行
# 既存のペアリング情報を削除
bluetoothctl
> remove [RASPBERRY_PI_MAC_ADDRESS]
> exit
```

### 4. デバッグ用コマンド

#### Raspberry Pi側
```bash
# GATTサービスの状態を確認
sudo dbus-send --system --print-reply --dest=org.bluez /org/bluez/hci0 org.freedesktop.DBus.ObjectManager.GetManagedObjects

# Bluetoothログの確認
sudo journalctl -u bluetooth -f
```

#### PC側
```bash
# Bluetoothアダプタの状態確認
hciconfig

# BLE接続の詳細ログ
sudo btmon
```

### 5. 代替案

もしGATTサービスの問題が解決しない場合：

1. **シンプルなテストサーバーの作成**
   - 最小限のGATTサービスだけを実装
   - 段階的に機能を追加

2. **別のBLEライブラリの使用**
   - PC側: `pygatt`や`bluepy`を試す
   - Raspberry Pi側: `bluezero`ライブラリを試す

3. **直接的なL2CAP接続**
   - GATTを使わずに直接データ送受信

## 次のステップ

1. `ble_scanner.py`を実行して詳細情報を取得
2. 取得した情報を基に問題を特定
3. 必要に応じてコードを修正