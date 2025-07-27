// BLE関連の定数
export const BLE_CONFIG = {
  DRONE_SERVICE_UUID: '6E400001-B5A3-F393-E0A9-E50E24DCCA9E',
  COMMAND_CHARACTERISTIC_UUID: '6E400002-B5A3-F393-E0A9-E50E24DCCA9E',
  STATUS_CHARACTERISTIC_UUID: '6E400003-B5A3-F393-E0A9-E50E24DCCA9E',
  DEVICE_NAME: 'RaspberryPiDrone',
  SCAN_TIMEOUT: 10000, // 10秒
} as const;

// ドローンコマンドの型定義
export interface DroneCommand {
  throttle: number; // 0-100
  pitch: number;    // -45 to 45
  roll: number;     // -45 to 45
  yaw: number;      // -180 to 180
}

// BLE接続状態
export type BleConnectionState = 
  | 'disconnected'
  | 'scanning'
  | 'connecting'
  | 'connected'
  | 'error';

// ドローンステータス
export interface DroneStatus {
  message: string;
  timestamp: Date;
}

// エラータイプ
export interface BleError {
  code: string;
  message: string;
}