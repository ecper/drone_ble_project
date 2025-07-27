# Flutter ドローンコントローラー

FlutterでBLE通信を使用してドローンを制御するiOSアプリです。

## セットアップ

### 1. Flutter環境の確認
```bash
flutter doctor
```

### 2. 依存関係のインストール
```bash
cd flutter_app
flutter pub get
```

### 3. iOSビルド
```bash
# iOSシミュレーターで実行
flutter run

# 実機で実行（デバイスを接続して）
flutter run -d [device_id]

# リリースビルド
flutter build ios
```

## 機能

- **BLE接続**: RaspberryPiDroneを自動検索・接続
- **スロットル制御**: 0-100%の10%刻みで調整
- **方向制御**: 前進・後退・左右移動
- **回転制御**: 左右回転
- **緊急停止**: 全モーター即座停止

## プロジェクト構造

```
flutter_app/
├── lib/
│   └── main.dart         # メインアプリケーション
├── ios/
│   └── Runner/
│       └── Info.plist    # iOS権限設定
└── pubspec.yaml          # 依存関係定義
```

## トラブルシューティング

### CocoaPodsエラーが発生する場合
```bash
cd ios
pod install
cd ..
flutter run
```

### Bluetoothが動作しない場合
1. iPhoneの設定 → Bluetooth → ON を確認
2. アプリの権限設定を確認
3. 実機でテスト（シミュレーターではBLEは動作しません）

## 開発メモ

- flutter_blue_plusライブラリを使用
- iOS 13.0以上が必要
- BLE権限はInfo.plistに設定済み