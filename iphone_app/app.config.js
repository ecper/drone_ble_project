export default {
  expo: {
    name: "Drone Controller",
    slug: "drone-controller",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    splash: {
      image: "./assets/splash.png",
      resizeMode: "contain",
      backgroundColor: "#ffffff"
    },
    assetBundlePatterns: ["**/*"],
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.yourcompany.dronecontroller",
      infoPlist: {
        NSBluetoothAlwaysUsageDescription: "このアプリはドローンとBluetooth通信を行うためにBluetoothを使用します。",
        NSBluetoothPeripheralUsageDescription: "このアプリはドローンとBluetooth通信を行うためにBluetoothを使用します。"
      }
    },
    plugins: []
  }
};