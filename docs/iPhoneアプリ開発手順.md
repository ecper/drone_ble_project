# iPhoneアプリ開発手順

## 1. 開発環境のセットアップ

### 必要なツール
- Node.js (v14以上)
- Expo CLI
- Xcode（iOSビルド用）
- iOS実機またはシミュレーター

### インストール手順

```bash
# ディレクトリ移動
cd /home/uchida/Documents/fov-prog/drone_ble_project/iphone_app

# Expo CLIのインストール（グローバル）
npm install -g expo-cli

# 依存関係のインストール
npm install

# iOSフォルダの生成（初回のみ）
npx expo prebuild --platform ios
```

## 2. アプリの起動

### 開発サーバーの起動
```bash
# Expo Dev Clientを使用
npx expo run:ios
```

### 実機での実行
1. iPhone実機をUSBで接続
2. Xcodeでプロジェクトを開く（ios/フォルダ）
3. Signing & Capabilitiesで開発者アカウントを設定
4. 実機を選択してビルド・実行

## 3. アプリの機能

### BLE接続機能
- 「接続」ボタンでRaspberryPiDroneを自動検索
- 10秒間スキャンして自動接続
- 接続状態をリアルタイム表示

### ドローン制御機能

#### スロットル制御（上下移動）
- **↑ 上昇**: スロットルを10%増加
- **↓ 下降**: スロットルを10%減少

#### 方向制御
- **前進**: ピッチ+10度
- **後退**: ピッチ-10度
- **左**: ロール-10度
- **右**: ロール+10度

#### 回転制御
- **↺ 左回転**: ヨー-10度
- **↻ 右回転**: ヨー+10度

#### 緊急停止
- **停止**: 全モーター停止コマンド送信

### コマンドフォーマット
```
T[スロットル],P[ピッチ],R[ロール],Y[ヨー]
例: T50,P10,R-5,Y0
```

## 4. トラブルシューティング

### ビルドエラー
```bash
# キャッシュクリア
npx expo start --clear

# node_modules再インストール
rm -rf node_modules
npm install

# iOSフォルダ再生成
rm -rf ios
npx expo prebuild --platform ios
```

### BLE接続できない
1. iPhoneのBluetooth設定を確認
2. 位置情報サービスが有効か確認
3. アプリの権限設定を確認（設定→アプリ→Bluetooth）

### コマンドが送信されない
- Raspberry Piのログを確認
- BLE接続が維持されているか確認
- コマンドフォーマットが正しいか確認

## 5. 開発のヒント

### デバッグ方法
```javascript
// App.jsにコンソールログを追加
console.log('Command sent:', command);
console.log('Status received:', data);
```

### カスタマイズ例

#### スロットル増加量の変更
```javascript
// App.jsの droneControl内
throttleUp: () => {
  const newThrottle = Math.min(throttle + 5, 100); // 5%ずつ増加
  // ...
}
```

#### 新しいコマンドの追加
```javascript
// 例：ホバリング
hover: () => sendCommand(`T${throttle},P0,R0,Y0`),
```

## 6. 本番ビルド

### TestFlightでの配布
```bash
# プロダクションビルド
npx expo build:ios

# または EAS Build使用
npm install -g eas-cli
eas build --platform ios
```

## 7. 注意事項

- **安全第一**: 実際のドローン制御時は広い場所で行う
- **バッテリー管理**: 低電圧時は自動停止機能を実装推奨
- **通信範囲**: BLEの有効範囲は約10-30m
- **レスポンス**: BLE通信には遅延があるため注意

## 8. 今後の拡張案

- ジョイスティックUI実装
- センサーデータの可視化
- フライトログ記録
- 自動飛行モード
- 映像ストリーミング対応