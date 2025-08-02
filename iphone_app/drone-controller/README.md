# ドローンコントローラー iPhoneアプリ

React Native Expoを使用したiPhone用ドローンコントローラーアプリです。

## 必要な環境

- Node.js (v16以上)
- npm または yarn
- EAS CLI (`npm install -g eas-cli`)
- Expo アカウント
- Apple Developer アカウント（実機テスト用）

## セットアップ手順

### 1. 依存関係のインストール

```bash
cd /Users/hoshinafumito/development/drone_ble_project/iphone_app/drone-controller
npm install
```

### 2. EASの設定

```bash
# EASにログイン
eas login

# プロジェクトIDを設定（初回のみ）
eas init
```

### 3. 開発用ビルドの作成

BLE機能を使用するため、カスタム開発クライアントが必要です：

```bash
# iOS用の開発ビルドを作成
eas build --profile development --platform ios
```

ビルドが完了したら、QRコードまたはリンクからiPhoneにインストールします。

### 4. 開発サーバーの起動

```bash
# 開発サーバーを起動
npx expo start --dev-client
```

### 5. アプリの起動

1. iPhoneで開発用ビルドを開く
2. 開発サーバーのQRコードをスキャン
3. アプリが起動します

## 使い方

1. **デバイススキャン**: 「デバイスをスキャン」ボタンをタップ
2. **接続**: リストから「RaspberryPiDrone」を選択
3. **操作**: 
   - 起動/停止ボタンでモーター制御
   - 方向ボタンで移動制御
   - PIDパラメータの調整
   - 緊急停止ボタンで即座に停止

## トラブルシューティング

### ビルドエラーの場合

```bash
# キャッシュをクリア
npx expo start -c

# node_modulesを再インストール
rm -rf node_modules
npm install
```

### BLE接続できない場合

1. iPhoneの設定でBluetoothがONになっているか確認
2. ラズパイでdrone_ble_server.pyが実行されているか確認
3. アプリの権限設定でBluetoothが許可されているか確認

## 注意事項

- iOS 18.5（iPhone 14）で動作確認済み
- Expo Goでは動作しません（BLE機能のため）
- 必ず開発用ビルド（Dev Client）を使用してください