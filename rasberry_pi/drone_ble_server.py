#!/usr/bin/env python3

import platform
import sys
import logging
import time
import base64
import binascii

# Platform detection
IS_RASPBERRY_PI = platform.machine().startswith('arm') or 'raspberry' in platform.node().lower()

print(f"Platform detected: {platform.system()} {platform.machine()}")
print(f"Running on Raspberry Pi: {IS_RASPBERRY_PI}")

# D-Bus related imports
try:
    import dbus
    import dbus.service  
    import dbus.exceptions
    import dbus.mainloop.glib
    DBUS_AVAILABLE = True
    print("D-Bus modules imported successfully")
except ImportError as e:
    print(f"D-Bus not available: {e}")
    DBUS_AVAILABLE = False

# GLib related imports
try:
    from gi.repository import GLib
    GLIB_AVAILABLE = True
    print("GLib imported successfully")
except ImportError as e:
    print(f"GLib not available: {e}")
    GLIB_AVAILABLE = False

# I2C library imports
try:
    import smbus2
    I2C_AVAILABLE = True
    print("I2C (smbus2) imported successfully")
except ImportError:
    print("I2C (smbus2) not available - using mock")
    I2C_AVAILABLE = False

# Check required dependencies
if not DBUS_AVAILABLE or not GLIB_AVAILABLE:
    print("Error: Required dependencies missing!")
    print("Please run: ./install_pc_ble_deps.sh")
    print("Or install manually:")
    print("  sudo apt install python3-gi python3-dbus bluez")
    print("  pip3 install PyGObject dbus-python")
    sys.exit(1)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- BlueZ D-Bus interface definitions (no change) ---
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE = 'org.bluez.GattDescriptor1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

# --- GATT service and characteristic UUIDs ---
# !!! IMPORTANT: Replace these with your own generated UUIDs !!!
DRONE_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
COMMAND_CHARACTERISTIC_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
STATUS_CHARACTERISTIC_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# --- Arduino I2C Settings ---
# Raspberry Pi 4/5 usually uses I2C bus 1.
# Arduino I2C slave address
I2C_BUS = 1 
ARDUINO_I2C_ADDRESS = 0x08 # Example: address set with Arduino Wire.begin(0x08);

# Mock I2C class (for PC environment)
class MockI2C:
    def __init__(self, bus=1):
        self.bus = bus
        logger.info(f"Mock I2C bus {bus} initialized")
    
    def write_i2c_block_data(self, addr, reg, data):
        """Simulate I2C write"""
        try:
            command_str = ''.join([chr(b) for b in data if 32 <= b <= 126])
            logger.info(f"Mock I2C write to 0x{addr:02X}: '{command_str}'")
        except Exception as e:
            logger.info(f"Mock I2C write to 0x{addr:02X}: {data} (raw bytes)")
        return True
    
    def read_i2c_block_data(self, addr, reg, length):
        """Simulate I2C read"""
        dummy_data = [0x00] * length
        logger.info(f"Mock I2C read from 0x{addr:02X}: {dummy_data}")
        return dummy_data
    
    def close(self):
        """Close bus"""
        logger.info("Mock I2C bus closed")

# I2C bus object
bus = None # Declared globally

# Global characteristic reference for notifications
status_characteristic_obj = None

# --- Helper functions etc. (borrowed from BlueZ samples, no change) ---
def find_adapter(bus_obj): # Changed to 'bus_obj' to avoid name collision with 'bus'
    remote_om = dbus.Interface(bus_obj.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for path, interfaces in objects.items():
        if (LE_ADVERTISING_MANAGER_IFACE in interfaces and 
            GATT_MANAGER_IFACE in interfaces):
            return path
    # Fallback: find adapter that supports at least one of the interfaces
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

# --- GATT service, characteristic, and descriptor classes (no change) ---
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
        logger.info(f"Readvalue called for {self.uuid}")
        logger.info(f"Options: {options}")
        return dbus.Array(b'Default Value', signature='y')

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        logger.info(f"Writevalue called for {self.uuid} with value: {bytes(value).decode('utf-8')}")

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
        logger.info(f"Readvalue called for descriptor {self.uuid}")
        return dbus.Array(b'Default Descriptor Value', signature='y')

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        logger.info(f"Writevalue called for descriptor {self.uuid} with value: {bytes(value).decode('utf-8')}")

# --- GATT service and characteristic implementation for drone control ---
class DroneService(Service):
    def __init__(self, bus_obj, index):
        super().__init__(bus_obj, index, DRONE_SERVICE_UUID, True)
        self.add_characteristic(CommandCharacteristic(bus_obj, 0, self))
        self.add_characteristic(StatusCharacteristic(bus_obj, 1, self))

class CommandCharacteristic(Characteristic):
    def __init__(self, bus_obj, index, service):
        # Write possible without security
        super().__init__(bus_obj, index, COMMAND_CHARACTERISTIC_UUID,
                         ['write-without-response'], service)

    def WriteValue(self, value, options):
        """
        Called when iPhone app writes data to COMMAND_CHARACTERISTIC.
        """
        try:
            # debug: received data detail information
            logger.info(f"Raw value type: {type(value)}, length: {len(value)}")
            logger.info(f"Raw value bytes: {[hex(b) for b in value]}")
            
            # empty data check
            if not value or len(value) == 0:
                logger.warning("Received empty BLE command")
                GLib.idle_add(send_status_notification, "ERR:Empty_CMD")
                return
            
            # Base64 decode attempt
            try:
                # first get raw byte data as UTF-8 string
                base64_str = bytes(value).decode('utf-8').strip()
                logger.info(f"Received Base64 string: '{base64_str}'")
                
                # Base64 decode
                decoded_bytes = base64.b64decode(base64_str)
                command_str = decoded_bytes.decode('utf-8').strip()
                logger.info(f"Decoded command: '{command_str}'")
            except (binascii.Error, ValueError) as b64_err:
                logger.warning(f"Base64 decode failed: {b64_err}, trying direct UTF-8 decode")
                # If Base64 decode fails, try direct UTF-8 decode (for compatibility)
                command_str = bytes(value).decode('utf-8').strip()
                logger.info(f"Direct decoded command: '{command_str}'")

            # empty string check
            if not command_str:
                logger.warning("Command string is empty after decoding")
                GLib.idle_add(send_status_notification, "ERR:Empty_STR")
                return

            # transmit command to Arduino via I2C
            if bus: # check if I2C bus is initialized
                # convert string to byte list
                data_bytes = [ord(char) for char in command_str]
                # write to Arduino via I2C (using write_i2c_block_data)
                try:
                    bus.write_i2c_block_data(ARDUINO_I2C_ADDRESS, 0, data_bytes) # 0 is register address (arbitrary)
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
            # try processing as raw byte data
            try:
                # extract only ASCII range characters
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
        self.notifying = False # manage notification state

    def ReadValue(self, options):
        """
        Called when iPhone app tries to read data from STATUS_CHARACTERISTIC.
        """
        current_status = b"OK:Ready" 
        logger.info(f"Status read requested. Sending: '{current_status.decode()}'")
        return dbus.Array(current_status, signature='y')

    def StartNotify(self):
        """
        Called when iPhone app begins notification subscription.
        """
        if self.notifying:
            logger.info("Already notifying.")
            return

        self.notifying = True
        logger.info("Started notifying for StatusCharacteristic.")

    def StopNotify(self):
        """
        Called when iPhone app stops notification subscription.
        """
        if not self.notifying:
            logger.info("Not notifying.")
            return

        self.notifying = False
        logger.info("Stopped notifying for StatusCharacteristic.")

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties, invalidated_properties):
        """
        Helper function to send GATTCharacteristic1 interface PropertiesChanged signal.
        This can notify subscribing clients of value changes.
        """
        pass

def send_status_notification(status_message: str):
    """
    Update drone status and send notification to subscribing iPhone app.
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
    return GLib.SOURCE_REMOVE # when called from GLib.idle_add, execute once and end

# --- BLE advertisement class (no change) ---
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
        # BLE peripheral behavior without pairing requirement
        self.discoverable = True
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
        # BLE peripheral behavior (no pairing required)
        properties['Discoverable'] = dbus.Boolean(True)
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

# --- system requirements check function ---
def check_system_requirements():
    """check system requirements"""
    import os
    import subprocess
    
    # check I2C device file existence
    i2c_device = f"/dev/i2c-{I2C_BUS}"
    if not os.path.exists(i2c_device):
        logger.error(f"I2C device {i2c_device} not found. Please enable I2C interface.")
        logger.error("Run: sudo raspi-config -> Interface Options -> I2C -> Enable")
        return False
    
    # check BlueZ existence
    try:
        subprocess.run(["which", "bluetoothctl"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        logger.error("BlueZ (bluetoothctl) not found. Please install BlueZ.")
        logger.error("Run: sudo apt-get install bluez")
        return False
    
    # check Bluetooth service status
    try:
        result = subprocess.run(["systemctl", "is-active", "bluetooth"], 
                              capture_output=True, text=True)
        if result.stdout.strip() != "active":
            logger.error("Bluetooth service is not active. Starting...")
            subprocess.run(["sudo", "systemctl", "start", "bluetooth"], check=True)
    except Exception as e:
        logger.warning(f"Could not check/start bluetooth service: {e}")
    
    return True

# --- Main function ---
def setup_bluetooth_no_pairing():
    """disable Bluetooth pairing requirement"""
    import subprocess
    try:
        # Set no pairing required with bluetoothctl
        commands = [
            ["bluetoothctl", "power", "on"],
            ["bluetoothctl", "pairable", "on"],
            ["bluetoothctl", "discoverable", "on"],
            ["bluetoothctl", "agent", "NoInputNoOutput"],
            ["bluetoothctl", "default-agent"]
        ]
        for cmd in commands:
            subprocess.run(cmd, capture_output=True)
        logger.info("Bluetooth configured for no pairing")
    except Exception as e:
        logger.warning(f"Could not configure bluetooth: {e}")

def main():
    global bus, status_characteristic_obj # set I2C bus object as global as well

    # 0. check system requirements
    if not check_system_requirements():
        logger.error("System requirements not met. Exiting.")
        sys.exit(1)
    
    # Bluetooth pairing settings
    setup_bluetooth_no_pairing()

    # 1. I2C bus initialization
    global bus
    if I2C_AVAILABLE:
        try:
            bus = smbus2.SMBus(I2C_BUS) # open I2C bus
            logger.info(f"Successfully opened I2C bus {I2C_BUS}.")
        except Exception as e:
            logger.error(f"Failed to open I2C bus: {e}. Using mock I2C.")
            bus = MockI2C()
    else:
        logger.info("I2C not available, using mock I2C")
        bus = MockI2C()

    # 2. D-Bus and adapter initialization
    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        dbus_bus = dbus.SystemBus() # change variable name to avoid D-Bus object name collision
        
        # check Bluetooth adapter existence
        adapter_path = find_adapter(dbus_bus)
        if adapter_path is None:
            logger.error("No Bluetooth adapter found. Please check if Bluetooth is enabled.")
            sys.exit(1)
        
        logger.info(f"Found Bluetooth adapter: {adapter_path}")
        
    except Exception as e:
        logger.error(f"Failed to initialize D-Bus or find Bluetooth adapter: {e}")
        sys.exit(1)

    # 3. register GATT application, service, and characteristics
    app = Application(dbus_bus)
    drone_service = DroneService(dbus_bus, 0)
    app.add_service(drone_service)
    
    # save StatusCharacteristic instance to global variable
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

    # 4. Register BLE advertisement
    ad_manager = dbus.Interface(
        dbus_bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        LE_ADVERTISING_MANAGER_IFACE)

    advertisement = Advertisement(dbus_bus, 0, 'peripheral')
    advertisement.add_service_uuid(DRONE_SERVICE_UUID)
    advertisement.add_local_name("RaspberryPiDrone") # Set device name
    advertisement.include_tx_power = True  # Include transmission power (tip for no pairing required)

    logger.info("Registering BLE Advertisement...")
    ad_manager.RegisterAdvertisement(advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    # 5. Start GLib main loop
    logger.info("BLE Peripheral started. Advertising and waiting for Connects...")
    
    # GLib integrated loop to regularly read I2C data from Arduino and send notifications
    def arduino_reader_loop():
        if bus: # check if I2C bus is initialized
            try:
                # Read data from Arduino via I2C (example: 10 bytes)
                # Arduino sketch needs to be prepared so data can be read with read_i2c_block_data
                # Example: make Arduino return data with Wire.onRequest
                # data_from_arduino = bus.read_i2c_block_data(ARDUINO_I2C_ADDRESS, 0, 10) 
                
                # generate dummy data here
                dummy_status_from_arduino = f"Arduino_Loop:{int(time.time()) % 100}"
                if dummy_status_from_arduino:
                    logger.debug(f"Received (dummy) from Arduino via I2C: '{dummy_status_from_arduino}'")
                    # if data received via I2C is valid, send BLE notification
                    send_status_notification(f"I2C_DATA:{dummy_status_from_arduino}")
            except Exception as e:
                logger.error(f"Error reading from Arduino via I2C: {e}")
        return True # return True to continue loop

    GLib.timeout_add(500, arduino_reader_loop) # attempt to read from Arduino every 500ms

    # start main loop
    mainloop = GLib.MainLoop()
    try:
        mainloop.run()
    except KeyboardInterrupt:
        logger.info("BLE Peripheral Stopped by user (Ctrl+C).")
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
