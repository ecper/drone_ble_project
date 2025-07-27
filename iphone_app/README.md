# ドローンコントローラー iOS アプリ

React Native + TypeScriptで開発したiOS専用のドローン制御アプリです。

## 必要な環境

- macOS（Xcodeが必要）
- Node.js v14以上
- Xcode 13以上
- iOS 13.0以上のiPhoneまたはiPad

## セットアップ

### 1. 依存関係のインストール
```bash
cd iphone_app
npm install
```

### 2. iOSビルド
```bash
# プレビルドを生成
npx expo prebuild --platform ios

# または、直接実行
npx expo run:ios
```

### 3. 実機での実行
1. iPhoneをUSBケーブルでMacに接続
2. Xcodeでプロジェクトを開く：`open ios/DroneController.xcworkspace`
3. Signing & Capabilitiesで開発者アカウントを設定
4. 実機を選択してビルド

## 機能

### BLE接続
- RaspberryPiDroneを自動検索
- ワンタップで接続・切断

### ドローン制御
- **スロットル制御**: 上昇・下降（10%刻み）
- **方向制御**: 前進・後退・左右移動
- **回転制御**: 左右回転
- **緊急停止**: 全モーター即座停止

### 操作方法
- **短押し**: 通常の動作（ピッチ/ロール/ヨー ±10）
- **長押し**: 強い動作（ピッチ/ロール/ヨー ±20, ±30）

## トラブルシューティング

### ビルドエラーが発生する場合
```bash
# クリーンビルド
cd ios
rm -rf Pods Podfile.lock
pod install
cd ..
npx expo run:ios
```

### BLE接続できない場合
1. iPhoneの設定 → Bluetooth → ONを確認
2. Raspberry Piが正常に動作しているか確認
3. アプリを再起動

### 開発時の注意点
- Expo GoではBLEが動作しないため、必ず開発ビルドを使用すること
- react-native-ble-plxはネイティブモジュールのため、プレビルドが必要

## プロジェクト構造
```
iphone_app/
├── App.tsx              # メインコンポーネント
├── src/
│   ├── components/      # UIコンポーネント
│   │   ├── ConnectionButton.tsx
│   │   ├── DroneControl.tsx
│   │   └── StatusDisplay.tsx
│   ├── services/        # ビジネスロジック
│   │   ├── BleService.ts
│   │   └── BleServiceTypes.ts
│   └── types/           # 型定義
│       └── ble.types.ts
└── ios/                 # iOSネイティブコード（自動生成）
```