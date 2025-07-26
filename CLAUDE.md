# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code)向けのガイダンスを提供します。

## プロジェクト概要

自作ドローン制御システムの開発プロジェクトです。システムは以下の3つの主要コンポーネントで構成されています：

1. **iPhoneアプリ** (React Native Expo): ユーザーインターフェース、BLE通信
2. **Raspberry Pi 5**: BLEサーバー、メインコントローラー、I2Cマスター
3. **Arduino**: 低レベル制御、モーター/ESC制御、センサーデータ収集

### 通信フロー
- iPhone → Raspberry Pi: BLE（Bluetooth Low Energy）
- Raspberry Pi → Arduino: I2C（Inter-Integrated Circuit）
- Arduino → モーター: PWM（Pulse Width Modulation）

## 現在のプロジェクト状況

- **実装済み**: Raspberry Pi用BLEサーバー (`drone_ble_server.py`)
- **未実装**: 
  - iPhoneアプリ (React Native Expo)
  - Arduinoスケッチ
  - ESC/モーター制御ロジック

## システムアーキテクチャ

### 1. Raspberry Pi側 (drone_ble_server.py)

**BLEサーバー機能**
- D-BusとBlueZ APIを使用
- GATTサーバーの実装
- BLEアドバタイジング（デバイス名: "RaspberryPiDrone"）

**GATTサービス構造**
- サービスUUID: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
- コマンド特性: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (write, write-without-response)
- ステータス特性: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (read, notify)

**I2C設定**
- バス: 1 (Raspberry Pi 4/5の標準)
- Arduinoアドレス: 0x08
- smbus2ライブラリを使用

### 2. iPhoneアプリ側 (未実装)

**技術スタック**
- React Native Expo
- react-native-ble-plx ライブラリ
- Expo Dev Client（Expo Goでは動作しない）

**主要機能**
- BLEスキャンとデバイス接続
- ジョイスティックUIによる操作
- コマンド送信（例: "T1500,P10,R20,Y-5"）
- ステータス受信と表示

### 3. Arduino側 (未実装)

**主要機能**
- I2Cスレーブとして動作
- モーター/ESC制御（PWM信号）
- センサーデータ収集（IMU等）
- PID制御による飛行安定化

## 開発コマンド

### サーバーの実行
```bash
# Python 3で実行
python3 drone_ble_server.py

# 権限エラーが発生した場合はsudoで実行
sudo python3 drone_ble_server.py
```

### システム要件
```bash
# I2Cインターフェースを有効化
sudo raspi-config
# Interface Options → I2C → Enable に移動

# 必要なシステムパッケージをインストール
sudo apt-get install bluez python3-dbus python3-gi

# Python依存関係をインストール
pip3 install smbus2
```

### デバッグ
```bash
# Bluetoothサービスの状態を確認
systemctl status bluetooth

# 実行中のシステムログを監視
journalctl -f | grep -i bluetooth

# I2Cデバイスを確認
i2cdetect -y 1

# BLEアドバタイジングをテスト
sudo hcitool lescan
```

## コード構造

### 主要クラス
- `Application`: GATTサービスを管理するD-Busオブジェクト
- `DroneService`: ドローン制御用のカスタムGATTサービス
- `CommandCharacteristic`: iPhoneからの書き込み操作を処理
- `StatusCharacteristic`: iPhoneへの読み取り/通知操作を処理
- `Advertisement`: BLEアドバタイジングを管理

### 主要関数
- `main()`: エントリーポイント、I2C、D-Busを初期化し、サービスを開始
- `send_status_notification()`: 接続されたデバイスにBLE通知を送信
- `arduino_reader_loop()`: 定期的なI2Cポーリング（現在はダミーデータを使用）
- `check_system_requirements()`: システム設定を検証

### エラーハンドリング
- I2C通信エラーはキャッチされ、ログに記録される
- BLE登録の失敗はアプリケーションの終了をトリガー
- ステータス通知にはエラーコードが含まれる（例: "ERR:I2C_Not_Ready"）

## 開発フェーズ

### フェーズ1: Raspberry PiのBLE・I2C環境構築とテスト
- Raspberry Pi OSの更新とI2C有効化
- Python環境構築とdrone_ble_server.pyの動作確認
- Arduino I2Cスレーブの基本実装とテスト

### フェーズ2: iPhoneアプリ開発と連携テスト
- React Native Expoプロジェクトのセットアップ
- BLEクライアント機能の実装
- Raspberry Piとの通信テスト

### フェーズ3: ドローン制御ロジックの実装
- Arduinoフライトコントローラーの実装
- PID制御とモーター制御
- 安全性テストと調整

## 重要な注意事項

1. **開発環境**: drone_ble_server.pyはRaspberry Pi上で動作するものであり、開発PCでは実行しない

2. **I2C通信**: 
   - arduino_reader_loopは現在ダミーデータを生成している
   - Raspberry Pi (3.3V) とArduino (5V) 間にはロジックレベルコンバーターが必要

3. **権限**: Raspberry Pi上でBLE操作にはsudoが必要

4. **UUID**: 現在のUUIDは例であり、本番環境では独自に生成したUUIDに置き換える

5. **ハードウェア**:
   - モーター: MT2204-2300KV ブラシレスDCモーター
   - ESC（Electronic Speed Controller）が必要
   - IMU等のセンサーが必要

## プロジェクト構造（推奨）

```
drone_ble_project/
├── raspberry_pi/
│   └── drone_ble_server.py    # 実装済み
├── arduino/
│   └── drone_controller/      # 未実装
│       └── drone_controller.ino
├── iphone_app/                # 未実装
│   ├── package.json
│   ├── app.json
│   └── src/
│       └── App.js
└── docs/
    └── 設計書.md