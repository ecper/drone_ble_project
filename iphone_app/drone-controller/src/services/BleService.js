import { BleManager } from 'react-native-ble-plx';
import { Platform, PermissionsAndroid } from 'react-native';
import base64 from 'base-64';

// BLE UUIDs (Raspberry Piと同じものを使用)
const DRONE_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
const COMMAND_CHARACTERISTIC_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e";
const STATUS_CHARACTERISTIC_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e";

class BleService {
  constructor() {
    this.manager = new BleManager();
    this.device = null;
    this.characteristics = {};
    this.statusCallback = null;
  }

  async requestPermissions() {
    if (Platform.OS === 'android') {
      const granted = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      ]);
      
      const allGranted = Object.values(granted).every(
        permission => permission === PermissionsAndroid.RESULTS.GRANTED
      );
      
      if (!allGranted) {
        throw new Error('Bluetooth permissions not granted');
      }
    }
    // iOS permissions are handled in Info.plist
    return true;
  }

  async scanForDevices(onDeviceFound) {
    await this.requestPermissions();
    
    this.manager.startDeviceScan(null, null, (error, device) => {
      if (error) {
        console.error('Scan error:', error);
        return;
      }
      onDeviceFound(device);
    });
  }

  stopScan() {
    this.manager.stopDeviceScan();
  }

  async connectToDevice(deviceId) {
    try {
      // デバイスに接続
      this.device = await this.manager.connectToDevice(deviceId);
      console.log('Connected to device');

      // サービスとキャラクタリスティックを探索
      await this.device.discoverAllServicesAndCharacteristics();
      
      // サービスを取得
      const services = await this.device.services();
      const droneService = services.find(service => 
        service.uuid.toLowerCase() === DRONE_SERVICE_UUID.toLowerCase()
      );

      if (!droneService) {
        throw new Error('Drone service not found');
      }

      // キャラクタリスティックを取得
      const characteristics = await droneService.characteristics();
      
      console.log('Found characteristics:');
      characteristics.forEach(char => {
        console.log('- UUID:', char.uuid);
        console.log('  Properties:', char.properties);
        const uuid = char.uuid.toLowerCase();
        if (uuid === COMMAND_CHARACTERISTIC_UUID.toLowerCase()) {
          this.characteristics.command = char;
          console.log('  -> Command characteristic found');
        } else if (uuid === STATUS_CHARACTERISTIC_UUID.toLowerCase()) {
          this.characteristics.status = char;
          console.log('  -> Status characteristic found');
        }
      });

      // ステータス通知を購読
      if (this.characteristics.status) {
        try {
          // 通知を有効化
          await this.characteristics.status.monitor((error, characteristic) => {
            if (error) {
              console.error('Monitor error:', error);
              return;
            }
            
            if (characteristic && this.statusCallback) {
              try {
                // Base64デコード
                const decodedValue = base64.decode(characteristic.value);
                this.statusCallback(decodedValue);
              } catch (decodeError) {
                console.error('Decode error:', decodeError);
              }
            }
          });
          console.log('Status monitoring started');
        } catch (monitorError) {
          console.warn('Could not enable notifications:', monitorError);
          // 通知が失敗してもアプリは続行
        }
      }

      return true;
    } catch (error) {
      console.error('Connection error:', error);
      throw error;
    }
  }

  async sendCommand(command) {
    if (!this.device || !this.characteristics.command) {
      throw new Error('Not connected');
    }

    try {
      // Base64エンコード
      const base64Value = base64.encode(command);
      await this.characteristics.command.writeWithoutResponse(base64Value);
      console.log('Command sent:', command);
    } catch (error) {
      console.error('Send command error:', error);
      throw error;
    }
  }

  async disconnect() {
    if (this.device) {
      await this.device.cancelConnection();
      this.device = null;
      this.characteristics = {};
    }
  }

  onStatusUpdate(callback) {
    this.statusCallback = callback;
  }

  isConnected() {
    return this.device !== null;
  }
}

export default new BleService();