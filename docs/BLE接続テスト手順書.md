# BLE接続テスト手順書

このドキュメントでは、Raspberry PiのBLEサーバーとiPhoneの接続をテストする手順を説明します。

## 前提条件

- Raspberry Piで`drone_ble_server.py`が正常に起動していること
- iPhoneがBLE対応機種であること（iPhone 4S以降）
- iPhoneのBluetoothが有効になっていること

## テスト方法

### 方法1: BLEスキャナーアプリを使用（推奨）

#### 1. アプリのインストール

App Storeから以下のいずれかのBLEスキャナーアプリをインストール：

- **LightBlue** (無料、初心者向け)
- **nRF Connect** (無料、詳細な情報が見れる)
- **BLE Scanner** (無料)

#### 2. LightBlueでの接続テスト手順

1. **アプリを起動**
   - LightBlueアプリを開く
   - 位置情報の使用許可を求められた場合は「許可」を選択

2. **デバイスのスキャン**
   - アプリが自動的に周囲のBLEデバイスをスキャン開始
   - リストに「RaspberryPiDrone」が表示されるまで待つ
   - 表示されない場合は画面を下にスワイプして更新

3. **デバイスに接続**
   - 「RaspberryPiDrone」をタップして接続
   - 接続成功すると、サービス一覧が表示される

4. **サービスとキャラクタリスティックの確認**
   - サービスUUID `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` を探す
   - サービスをタップして展開
   - 以下のキャラクタリスティックが表示されることを確認：
     - `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (Write)
     - `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (Read, Notify)

5. **読み取りテスト**
   - `6E400003...` (STATUS_CHARACTERISTIC) をタップ
   - 「Read」ボタンをタップ
   - 「OK:Ready」のようなステータスが表示されることを確認

6. **書き込みテスト**
   - `6E400002...` (COMMAND_CHARACTERISTIC) をタップ
   - 「Write」セクションで「Text」を選択
   - テストコマンドを入力（例: `T50,P0,R0,Y0`）
   - 「Write」ボタンをタップ
   - Raspberry Piのターミナルでコマンドが受信されたログを確認

7. **通知テスト**
   - `6E400003...` (STATUS_CHARACTERISTIC) をタップ
   - 「Listen for notifications」をONにする
   - Raspberry Piから送信される通知が表示されることを確認

#### 3. nRF Connectでの接続テスト手順

1. **アプリを起動**
   - nRF Connectアプリを開く
   - 「SCANNER」タブを選択

2. **デバイスのスキャン**
   - 「SCAN」ボタンをタップ
   - 「RaspberryPiDrone」を探す
   - デバイス名の横にRSSI値（信号強度）が表示される

3. **デバイスに接続**
   - 「RaspberryPiDrone」の「CONNECT」ボタンをタップ
   - 接続成功すると「CLIENT」タブに自動的に移動

4. **サービスの確認**
   - 「Unknown Service」として表示される場合もある
   - UUID `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` を確認

5. **キャラクタリスティックのテスト**
   - 各キャラクタリスティックの右側の矢印アイコンをタップ
   - Read: 下向き矢印をタップしてデータ読み取り
   - Write: 上向き矢印をタップ、データ入力して送信
   - Notify: ベルアイコンをタップして通知を有効化

### 方法2: 簡易確認（設定アプリ）

1. iPhoneの「設定」→「Bluetooth」を開く
2. 「その他のデバイス」に「RaspberryPiDrone」が表示されることを確認
   - ただし、設定アプリからは接続できません（BLEペリフェラルのため）
   - 表示されることでアドバタイジングが機能していることを確認できます

## トラブルシューティング

### デバイスが見つからない場合

1. **Raspberry Pi側の確認**
   ```bash
   # BLEサーバーが実行中か確認
   ps aux | grep drone_ble_server
   
   # Bluetoothアダプターの状態確認
   hciconfig hci0
   
   # アドバタイジングが有効か確認
   sudo hcitool lescan
   ```

2. **iPhone側の確認**
   - Bluetoothが有効になっているか確認
   - 機内モードになっていないか確認
   - アプリの権限設定を確認（設定→プライバシー→Bluetooth）

3. **距離を近づける**
   - Raspberry PiとiPhoneを1m以内に近づける

### 接続が不安定な場合

1. **干渉の確認**
   - 2.4GHz Wi-Fiルーターから離れる
   - 他のBluetooth機器を一時的にOFFにする

2. **Raspberry Piの再起動**
   ```bash
   # BLEサーバーを停止
   Ctrl + C
   
   # Bluetoothサービスを再起動
   sudo systemctl restart bluetooth
   
   # BLEサーバーを再実行
   sudo python3 drone_ble_server.py
   ```

## ログの確認方法

### Raspberry Pi側

```bash
# リアルタイムでログを確認
sudo journalctl -f -u bluetooth

# Python スクリプトのログを詳細表示
sudo python3 drone_ble_server.py 2>&1 | tee ble_test.log
```

### 期待されるログ出力例

**接続時**
```
2025-07-26 19:10:XX,XXX - INFO - Device connected: XX:XX:XX:XX:XX:XX
```

**コマンド受信時**
```
2025-07-26 19:10:XX,XXX - INFO - Received BLE command: 'T50,P0,R0,Y0'
2025-07-26 19:10:XX,XXX - INFO - Sent to Arduino via I2C: 'T50,P0,R0,Y0'
```

**通知送信時**
```
2025-07-26 19:10:XX,XXX - INFO - Notified status: 'CMD_RX:T50,P0,R0,Y0'
```

## 次のステップ

BLE接続が確認できたら：

1. **コマンドフォーマットの確認**
   - スロットル: T0-100 (%)
   - ピッチ: P-45-45 (度)
   - ロール: R-45-45 (度)
   - ヨー: Y-180-180 (度)
   - 例: `T50,P10,R-5,Y0`

2. **React Native アプリの開発**
   - iphone_app ディレクトリでアプリ開発を開始
   - react-native-ble-plx ライブラリを使用

3. **Arduino実装**
   - I2C通信の実装
   - モーター制御の実装