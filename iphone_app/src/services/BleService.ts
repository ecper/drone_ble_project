import { BleManager, Device } from 'react-native-ble-plx';
import { State } from './BleServiceTypes';
import { Buffer } from 'buffer';
import { BLE_CONFIG, DroneCommand } from '../types/ble.types';

export class BleService {
  private manager: BleManager;
  private device: Device | null = null;

  constructor() {
    this.manager = new BleManager();
  }

  // BLE状態を取得
  async getBleState(): Promise<State> {
    return await this.manager.state();
  }

  // BLE状態の監視
  onStateChange(callback: (state: State) => void): () => void {
    const subscription = this.manager.onStateChange(callback, true);
    return () => subscription.remove();
  }

  // デバイススキャン
  async scanForDevice(): Promise<Device> {
    return new Promise((resolve, reject) => {
      let found = false;
      const timeout = setTimeout(() => {
        if (!found) {
          this.manager.stopDeviceScan();
          reject(new Error('デバイスが見つかりませんでした'));
        }
      }, BLE_CONFIG.SCAN_TIMEOUT);

      this.manager.startDeviceScan(null, null, (error, device) => {
        if (error) {
          clearTimeout(timeout);
          this.manager.stopDeviceScan();
          reject(error);
          return;
        }

        if (device?.name === BLE_CONFIG.DEVICE_NAME) {
          found = true;
          clearTimeout(timeout);
          this.manager.stopDeviceScan();
          resolve(device);
        }
      });
    });
  }

  // デバイス接続
  async connectToDevice(device: Device): Promise<Device> {
    const connected = await device.connect();
    await connected.discoverAllServicesAndCharacteristics();
    this.device = connected;
    return connected;
  }

  // コマンド送信
  async sendCommand(command: string): Promise<void> {
    if (!this.device) {
      throw new Error('デバイスが接続されていません');
    }

    const base64Command = Buffer.from(command, 'utf-8').toString('base64');
    
    await this.device.writeCharacteristicWithoutResponseForService(
      BLE_CONFIG.DRONE_SERVICE_UUID,
      BLE_CONFIG.COMMAND_CHARACTERISTIC_UUID,
      base64Command
    );
  }

  // ドローンコマンドを送信
  async sendDroneCommand(command: DroneCommand): Promise<void> {
    const commandString = `T${command.throttle},P${command.pitch},R${command.roll},Y${command.yaw}`;
    await this.sendCommand(commandString);
  }

  // 停止コマンド
  async sendStopCommand(): Promise<void> {
    await this.sendCommand('STOP');
  }

  // ステータス監視
  async monitorStatus(callback: (status: string) => void): Promise<() => void> {
    if (!this.device) {
      throw new Error('デバイスが接続されていません');
    }

    const subscription = await this.device.monitorCharacteristicForService(
      BLE_CONFIG.DRONE_SERVICE_UUID,
      BLE_CONFIG.STATUS_CHARACTERISTIC_UUID,
      (error, characteristic) => {
        if (error) {
          console.error('Monitor error:', error);
          return;
        }

        if (characteristic?.value) {
          const status = Buffer.from(characteristic.value, 'base64').toString('utf-8');
          callback(status);
        }
      }
    );

    return () => subscription.remove();
  }

  // ステータス読み取り
  async readStatus(): Promise<string> {
    if (!this.device) {
      throw new Error('デバイスが接続されていません');
    }

    const characteristic = await this.device.readCharacteristicForService(
      BLE_CONFIG.DRONE_SERVICE_UUID,
      BLE_CONFIG.STATUS_CHARACTERISTIC_UUID
    );

    if (characteristic.value) {
      return Buffer.from(characteristic.value, 'base64').toString('utf-8');
    }

    return '';
  }

  // 切断
  async disconnect(): Promise<void> {
    if (this.device) {
      await this.device.cancelConnection();
      this.device = null;
    }
  }

  // デバイスが接続されているか
  isConnected(): boolean {
    return this.device !== null;
  }

  // クリーンアップ
  destroy(): void {
    this.manager.destroy();
  }
}