const { withInfoPlist } = require('@expo/config-plugins');

module.exports = function withBLE(config) {
  return withInfoPlist(config, (config) => {
    config.modResults.NSBluetoothAlwaysUsageDescription = 
      config.modResults.NSBluetoothAlwaysUsageDescription || 
      'このアプリはドローンとBluetooth通信を行うためにBluetoothを使用します。';
    
    config.modResults.NSBluetoothPeripheralUsageDescription = 
      config.modResults.NSBluetoothPeripheralUsageDescription || 
      'このアプリはドローンとBluetooth通信を行うためにBluetoothを使用します。';
    
    return config;
  });
};