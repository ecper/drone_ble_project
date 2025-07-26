#!/usr/bin/env python3

import dbus
import dbus.service
import dbus.exceptions
import dbus.mainloop.glib
from gi.repository import GLib
import sys
import logging
import time

# I2Cライブラリをインポート
try:
    import smbus2
except ImportError:
    print("smbus2 library not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "smbus2"])
    import smbus2 

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- BlueZ D-Bus インターフェース定義 (変更なし) ---
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE = 'org.bluez.GattDescriptor1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

# --- GATTサービスとキャラクタリスティックのUUID ---
# !!! 重要: これらはご自身で生成したUUIDに置き換えてください !!!
DRONE_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
COMMAND_CHARACTERISTIC_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
STATUS_CHARACTERISTIC_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# --- Arduino I2C設定 ---
# Raspberry Pi 4/5では通常I2Cバス1を使用します。
# Arduinoに設定するI2Cスレーブアドレス
I2C_BUS = 1 
ARDUINO_I2C_ADDRESS = 0x08 # 例: ArduinoのWire.begin(0x08); で設定するアドレス

# I2Cバスオブジェクト
bus = None # グローバルで宣言

# 通知用のグローバルなキャラクタリスティック参照
status_characteristic_obj = None

# --- ヘルパー関数など (BlueZサンプルからの流用、変更なし) ---
def find_adapter(bus_obj): # 'bus' と名前が衝突するため 'bus_obj' に変更
    remote_om = dbus.Interface(bus_obj.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for path, interfaces in objects.items():
        if (LE_ADVERTISING_MANAGER_IFACE in interfaces and 
            GATT_MANAGER_IFACE in interfaces):
            return path
    # フォールバック: どちらか一方でもサポートしているアダプターを探す
    for path, interfaces in objects.items():
        if (LE_ADVERTISING_MANAGER_IFACE in interfaces or 
            GATT_MANAGER_IFACE in interfaces):
            return path
    return None

class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidArguments'

class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'

class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'

class NotAuthorizedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotAuthorized'

# --- GATTサービス、キャラクタリスティック、ディスクリプタのクラス (変更なし) ---
class Application(dbus.service.Object):
    def __init__(self, bus_obj):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus_obj, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for characteristic in service.get_characteristics():
                response[characteristic.get_path()] = characteristic.get_properties()
                for descriptor in characteristic.get_descriptors():
                    response[descriptor.get_path()] = descriptor.get_properties()
        return response

class Service(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus_obj, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus_obj, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    self.get_characteristic_paths(),
                    signature='o'
                )
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristics(self):
        return self.characteristics

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

class Characteristic(dbus.service.Object):
    def __init__(self, bus_obj, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus_obj, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': dbus.Array(self.flags, signature='s'),
                'Descriptors': dbus.Array(
                    self.get_descriptor_paths(),
                    signature='o'
                )
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptors(self):
        return self.descriptors

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        logger.info(f"ReadValue called for {self.uuid}")
        return dbus.Array(b'Default Value', signature='y')

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        logger.info(f"WriteValue called for {self.uuid} with value: {bytes(value).decode('utf-8')}")

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        logger.info(f"StartNotify called for {self.uuid}")

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        logger.info(f"StopNotify called for {self.uuid}")

    @dbus.service.method(GATT_CHRC_IFACE)
    def Confirm(self):
        logger.info(f"Confirm called for {self.uuid}")

class Descriptor(dbus.service.Object):
    def __init__(self, bus_obj, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus_obj, self.path)

    def get_properties(self):
        return {
            GATT_DESC_IFACE: {
                'Characteristic': self.chrc.get_path(),
                'UUID': self.uuid,
                'Flags': dbus.Array(self.flags, signature='s'),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        logger.info(f"ReadValue called for descriptor {self.uuid}")
        return dbus.Array(b'Default Descriptor Value', signature='y')

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        logger.info(f"WriteValue called for descriptor {self.uuid} with value: {bytes(value).decode('utf-8')}")

# --- ドローン制御用のGATTサービスとキャラクタリスティックの実装 ---
class DroneService(Service):
    def __init__(self, bus_obj, index):
        super().__init__(bus_obj, index, DRONE_SERVICE_UUID, True)
        self.add_characteristic(CommandCharacteristic(bus_obj, 0, self))
        self.add_characteristic(StatusCharacteristic(bus_obj, 1, self))

class CommandCharacteristic(Characteristic):
    def __init__(self, bus_obj, index, service):
        super().__init__(bus_obj, index, COMMAND_CHARACTERISTIC_UUID,
                         ['write', 'write-without-response'], service)

    def WriteValue(self, value, options):
        """
        iPhoneアプリがCOMMAND_CHARACTERISTICにデータを書き込んだときに呼び出される。
        """
        try:
            # デバッグ: 受信したデータの詳細情報を表示
            logger.info(f"Raw value type: {type(value)}, length: {len(value)}")
            logger.info(f"Raw value bytes: {[hex(b) for b in value]}")
            
            # 空のデータチェック
            if not value or len(value) == 0:
                logger.warning("Received empty BLE command")
                GLib.idle_add(send_status_notification, "ERR:Empty_CMD")
                return
            
            # UTF-8デコード試行
            command_str = bytes(value).decode('utf-8').strip()
            logger.info(f"Received BLE command: '{command_str}'")

            # 空文字列チェック
            if not command_str:
                logger.warning("Command string is empty after decoding")
                GLib.idle_add(send_status_notification, "ERR:Empty_STR")
                return

            # I2CでArduinoにコマンドを送信
            if bus: # I2Cバスが初期化されているか確認
                # 文字列をバイトのリストに変換
                data_bytes = [ord(char) for char in command_str]
                # ArduinoにI2Cで書き込み (write_i2c_block_data を使用)
                try:
                    bus.write_i2c_block_data(ARDUINO_I2C_ADDRESS, 0, data_bytes) # 0はレジスタアドレス（任意）
                    logger.info(f"Sent to Arduino via I2C: '{command_str}'")
                    GLib.idle_add(send_status_notification, f"CMD_RX:{command_str[:15]}")
                except Exception as i2c_error:
                    logger.error(f"I2C write error: {i2c_error}")
                    GLib.idle_add(send_status_notification, "ERR:I2C_Write")
            else:
                logger.warning("I2C bus not initialized. Command not forwarded.")
                GLib.idle_add(send_status_notification, "ERR:I2C_Not_Ready")

        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode BLE data (not UTF-8): {e}")
            logger.error(f"Raw bytes that failed to decode: {[hex(b) for b in value]}")
            # 生のバイトデータとして処理を試みる
            try:
                # ASCII範囲内の文字のみ抽出
                ascii_chars = [chr(b) for b in value if 32 <= b <= 126]
                if ascii_chars:
                    command_str = ''.join(ascii_chars)
                    logger.info(f"Extracted ASCII command: '{command_str}'")
                    GLib.idle_add(send_status_notification, f"ASCII:{command_str[:13]}")
                else:
                    GLib.idle_add(send_status_notification, "ERR:No_ASCII")
            except Exception as extract_error:
                logger.error(f"Failed to extract ASCII: {extract_error}")
                GLib.idle_add(send_status_notification, "ERR:Decode")
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            GLib.idle_add(send_status_notification, f"ERR:{str(e)[:20]}")

class StatusCharacteristic(Characteristic):
    def __init__(self, bus_obj, index, service):
        super().__init__(bus_obj, index, STATUS_CHARACTERISTIC_UUID,
                         ['read', 'notify'], service)
        self.notifying = False # 通知状態を管理

    def ReadValue(self, options):
        """
        iPhoneアプリがSTATUS_CHARACTERISTICからデータを読み取ろうとしたときに呼び出される。
        """
        current_status = b"OK:Ready" 
        logger.info(f"Status read requested. Sending: '{current_status.decode()}'")
        return dbus.Array(current_status, signature='y')

    def StartNotify(self):
        """
        iPhoneアプリが通知を購読開始したときに呼び出される。
        """
        if self.notifying:
            logger.info("Already notifying.")
            return

        self.notifying = True
        logger.info("Started notifying for StatusCharacteristic.")

    def StopNotify(self):
        """
        iPhoneアプリが通知購読を停止したときに呼び出される。
        """
        if not self.notifying:
            logger.info("Not notifying.")
            return

        self.notifying = False
        logger.info("Stopped notifying for StatusCharacteristic.")

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties, invalidated_properties):
        """
        GATTCharacteristic1インターフェースのPropertiesChangedシグナルを送信するヘルパー関数。
        これにより、購読しているクライアントに値の変更を通知できる。
        """
        pass

def send_status_notification(status_message: str):
    """
    ドローンのステータスを更新し、購読しているiPhoneアプリに通知を送信する。
    """
    global status_characteristic_obj
    if status_characteristic_obj and status_characteristic_obj.notifying:
        try:
            value_bytes = dbus.Array(status_message.encode('utf-8'), signature='y')
            status_characteristic_obj.PropertiesChanged(
                GATT_CHRC_IFACE,
                {'Value': value_bytes},
                []
            )
            logger.info(f"Notified status: '{status_message}'")
        except Exception as e:
            logger.error(f"Error sending BLE notification: {e}")
    else:
        logger.debug(f"Status '{status_message}' not sent (no subscribers or char not ready).")
    return GLib.SOURCE_REMOVE # GLib.idle_add から呼ばれる場合、一度だけ実行して終了

# --- BLEアドバタイズメントのクラス (変更なし) ---
class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus_obj, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus_obj
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.include_tx_power = False
        dbus.service.Object.__init__(self, bus_obj, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature='s')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data, signature='sv')
        if self.include_tx_power is not None:
            properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)
        if hasattr(self, 'local_name') and self.local_name is not None:
            properties['LocalName'] = self.local_name
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_local_name(self, name):
        if not hasattr(self, 'local_name'):
            self.local_name = name

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

def register_ad_cb():
    logger.info('BLE Advertisement registered successfully.')

def register_ad_error_cb(error):
    logger.error(f'Failed to register advertisement: {error}')
    GLib.MainLoop().quit() 

def register_app_cb():
    logger.info('GATT Application registered successfully.')

def register_app_error_cb(error):
    logger.error(f'Failed to register application: {error}')
    GLib.MainLoop().quit()

# --- システム要件チェック関数 ---
def check_system_requirements():
    """システムの要件をチェックする"""
    import os
    import subprocess
    
    # I2Cデバイスファイルの存在確認
    i2c_device = f"/dev/i2c-{I2C_BUS}"
    if not os.path.exists(i2c_device):
        logger.error(f"I2C device {i2c_device} not found. Please enable I2C interface.")
        logger.error("Run: sudo raspi-config -> Interface Options -> I2C -> Enable")
        return False
    
    # BlueZの存在確認
    try:
        subprocess.run(["which", "bluetoothctl"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        logger.error("BlueZ (bluetoothctl) not found. Please install BlueZ.")
        logger.error("Run: sudo apt-get install bluez")
        return False
    
    # Bluetoothサービスの状態確認
    try:
        result = subprocess.run(["systemctl", "is-active", "bluetooth"], 
                              capture_output=True, text=True)
        if result.stdout.strip() != "active":
            logger.error("Bluetooth service is not active. Starting...")
            subprocess.run(["sudo", "systemctl", "start", "bluetooth"], check=True)
    except Exception as e:
        logger.warning(f"Could not check/start bluetooth service: {e}")
    
    return True

# --- メイン関数 ---
def main():
    global bus, status_characteristic_obj # I2Cバスオブジェクトもグローバルに設定

    # 0. システム要件のチェック
    if not check_system_requirements():
        logger.error("System requirements not met. Exiting.")
        sys.exit(1)

    # 1. I2Cバスの初期化
    try:
        bus = smbus2.SMBus(I2C_BUS) # I2Cバスを開く
        logger.info(f"Successfully opened I2C bus {I2C_BUS}.")
        # I2Cスレーブ（Arduino）が応答するか簡単なチェック（オプション）
        # bus.read_byte(ARDUINO_I2C_ADDRESS) 
    except Exception as e:
        logger.error(f"Failed to open I2C bus or communicate with Arduino: {e}. Is I2C enabled? Are connections correct?")
        sys.exit(1)

    # 2. D-Busとアダプターの初期化
    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        dbus_bus = dbus.SystemBus() # D-Busオブジェクトの名前衝突を避けるため変数名変更
        
        # Bluetoothアダプターの存在確認
        adapter_path = find_adapter(dbus_bus)
        if adapter_path is None:
            logger.error("No Bluetooth adapter found. Please check if Bluetooth is enabled.")
            sys.exit(1)
        
        logger.info(f"Found Bluetooth adapter: {adapter_path}")
        
    except Exception as e:
        logger.error(f"Failed to initialize D-Bus or find Bluetooth adapter: {e}")
        sys.exit(1)

    # 3. GATTアプリケーションとサービス、キャラクタリスティックの登録
    app = Application(dbus_bus)
    drone_service = DroneService(dbus_bus, 0)
    app.add_service(drone_service)
    
    # StatusCharacteristicのインスタンスをグローバル変数に保存
    for char in drone_service.get_characteristics():
        if char.uuid == STATUS_CHARACTERISTIC_UUID:
            status_characteristic_obj = char
            break
    
    if not status_characteristic_obj:
        logger.error("StatusCharacteristic not found. Exiting.")
        sys.exit(1)

    service_manager = dbus.Interface(
        dbus_bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        GATT_MANAGER_IFACE)

    logger.info("Registering GATT Application...")
    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)

    # 4. BLEアドバタイズメントの登録
    ad_manager = dbus.Interface(
        dbus_bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        LE_ADVERTISING_MANAGER_IFACE)

    advertisement = Advertisement(dbus_bus, 0, 'peripheral')
    advertisement.add_service_uuid(DRONE_SERVICE_UUID)
    advertisement.add_local_name("RaspberryPiDrone") # デバイス名を設定

    logger.info("Registering BLE Advertisement...")
    ad_manager.RegisterAdvertisement(advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    # 5. GLibメインループの開始
    logger.info("BLE Peripheral started. Advertising and waiting for connections...")
    
    # ArduinoからのI2Cデータを定期的に読み取り、通知を送信するループをGLibに統合
    def arduino_reader_loop():
        if bus: # I2Cバスが初期化されているか確認
            try:
                # ArduinoからI2Cでデータを読み取り (例: 10バイト)
                # Arduinoスケッチで、read_i2c_block_dataで読み取れるように準備しておく必要がある
                # 例: Arduino側でWire.onRequestでデータを返すようにする
                # data_from_arduino = bus.read_i2c_block_data(ARDUINO_I2C_ADDRESS, 0, 10) 
                
                # ここでは仮のデータを生成
                dummy_status_from_arduino = f"Arduino_Loop:{int(time.time()) % 100}"
                if dummy_status_from_arduino:
                    logger.debug(f"Received (dummy) from Arduino via I2C: '{dummy_status_from_arduino}'")
                    # I2Cで受信したデータが有効であれば、BLE通知を送信
                    send_status_notification(f"I2C_DATA:{dummy_status_from_arduino}")
            except Exception as e:
                logger.error(f"Error reading from Arduino via I2C: {e}")
        return True # ループを継続するためにTrueを返す

    GLib.timeout_add(500, arduino_reader_loop) # 500msごとにArduinoからの読み取りを試みる

    # メインループを開始
    mainloop = GLib.MainLoop()
    try:
        mainloop.run()
    except KeyboardInterrupt:
        logger.info("BLE Peripheral stopped by user (Ctrl+C).")
    finally:
        logger.info("Unregistering GATT Application and Advertisement...")
        try:
            service_manager.UnregisterApplication(app.get_path())
        except Exception as e:
            logger.warning(f"Failed to unregister application: {e}")
        try:
            ad_manager.UnregisterAdvertisement(advertisement.get_path())
        except Exception as e:
            logger.warning(f"Failed to unregister advertisement: {e}")

        logger.info("Application exited.")
        sys.exit(0)

if __name__ == '__main__':
    main()
