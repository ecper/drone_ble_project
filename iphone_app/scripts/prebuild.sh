#!/bin/bash

echo "📱 iOS向けドローンコントローラーアプリのビルド準備"

# 1. クリーンアップ
echo "🧹 クリーンアップ中..."
rm -rf ios android node_modules package-lock.json

# 2. 依存関係のインストール
echo "📦 依存関係をインストール中..."
npm install --force

# 3. Expoプレビルド（プラグインをスキップ）
echo "🔨 iOSプロジェクトを生成中..."
npx expo prebuild --platform ios

# 4. react-native-ble-plxの手動リンク
echo "🔗 BLEライブラリをリンク中..."
cd ios
pod install
cd ..

echo "✅ 準備完了！"
echo ""
echo "次のコマンドで実行できます："
echo "  npx expo run:ios --device"
echo ""
echo "または Xcode でプロジェクトを開く："
echo "  open ios/DroneController.xcworkspace"
