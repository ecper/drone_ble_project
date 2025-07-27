import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';
import 'dart:async';
import 'dart:io';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ドローンコントローラー',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const DroneControllerPage(),
    );
  }
}

class DroneControllerPage extends StatefulWidget {
  const DroneControllerPage({super.key});

  @override
  State<DroneControllerPage> createState() => _DroneControllerPageState();
}

class _DroneControllerPageState extends State<DroneControllerPage> {
  // BLE関連
  BluetoothDevice? _device;
  BluetoothCharacteristic? _commandCharacteristic;
  BluetoothCharacteristic? _statusCharacteristic;
  StreamSubscription<List<int>>? _statusSubscription;
  
  // 状態管理
  bool _isScanning = false;
  bool _isConnected = false;
  String _statusMessage = "";
  String _errorMessage = "";
  
  // ドローン制御値
  int _throttle = 0;
  
  // UUID定義
  static const String serviceUuid = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
  static const String commandUuid = "6e400002-b5a3-f393-e0a9-e50e24dcca9e";
  static const String statusUuid = "6e400003-b5a3-f393-e0a9-e50e24dcca9e";

  @override
  void initState() {
    super.initState();
    _initializeBle();
  }

  @override
  void dispose() {
    _disconnect();
    super.dispose();
  }

  Future<void> _initializeBle() async {
    // 権限リクエスト
    if (Platform.isIOS) {
      await Permission.bluetooth.request();
      await Permission.bluetoothScan.request();
      await Permission.bluetoothConnect.request();
    }
    
    // BLE状態監視
    FlutterBluePlus.adapterState.listen((state) {
      if (state != BluetoothAdapterState.on) {
        setState(() {
          _errorMessage = "Bluetoothを有効にしてください";
        });
      }
    });
  }

  Future<void> _scanForDevice() async {
    setState(() {
      _isScanning = true;
      _errorMessage = "";
    });

    try {
      // スキャン開始
      await FlutterBluePlus.startScan(
        timeout: const Duration(seconds: 10),
        withNames: ["RaspberryPiDrone"],
      );

      // デバイス検出を監視
      FlutterBluePlus.scanResults.listen((results) {
        for (ScanResult result in results) {
          if (result.device.platformName == "RaspberryPiDrone") {
            _connectToDevice(result.device);
            FlutterBluePlus.stopScan();
            break;
          }
        }
      });

      // タイムアウト処理
      await Future.delayed(const Duration(seconds: 10));
      if (!_isConnected) {
        setState(() {
          _errorMessage = "デバイスが見つかりませんでした";
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = "スキャンエラー: $e";
      });
    } finally {
      setState(() {
        _isScanning = false;
      });
    }
  }

  Future<void> _connectToDevice(BluetoothDevice device) async {
    try {
      setState(() {
        _device = device;
        _statusMessage = "接続中...";
      });

      // 接続
      await device.connect();
      
      // サービス検出
      List<BluetoothService> services = await device.discoverServices();
      
      for (BluetoothService service in services) {
        if (service.uuid.toString().toLowerCase() == serviceUuid) {
          for (BluetoothCharacteristic characteristic in service.characteristics) {
            String charUuid = characteristic.uuid.toString().toLowerCase();
            
            if (charUuid == commandUuid) {
              _commandCharacteristic = characteristic;
            } else if (charUuid == statusUuid) {
              _statusCharacteristic = characteristic;
              
              // 通知を有効化
              await characteristic.setNotifyValue(true);
              _statusSubscription = characteristic.lastValueStream.listen((value) {
                setState(() {
                  _statusMessage = String.fromCharCodes(value);
                });
              });
            }
          }
        }
      }

      setState(() {
        _isConnected = true;
        _statusMessage = "接続完了";
      });
    } catch (e) {
      setState(() {
        _errorMessage = "接続エラー: $e";
        _isConnected = false;
      });
    }
  }

  Future<void> _disconnect() async {
    _statusSubscription?.cancel();
    await _device?.disconnect();
    
    setState(() {
      _device = null;
      _commandCharacteristic = null;
      _statusCharacteristic = null;
      _isConnected = false;
      _statusMessage = "";
      _throttle = 0;
    });
  }

  Future<void> _sendCommand({
    int? throttle,
    int pitch = 0,
    int roll = 0,
    int yaw = 0,
  }) async {
    if (_commandCharacteristic == null) return;

    try {
      final command = "T${throttle ?? _throttle},P$pitch,R$roll,Y$yaw";
      await _commandCharacteristic!.write(command.codeUnits);
      
      if (throttle != null) {
        setState(() {
          _throttle = throttle;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = "送信エラー: $e";
      });
    }
  }

  Future<void> _emergencyStop() async {
    await _sendCommand(throttle: 0);
    setState(() {
      _statusMessage = "緊急停止";
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ドローンコントローラー'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              // ステータス表示
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('接続状態:'),
                          Text(
                            _isConnected ? '接続済み' : _isScanning ? 'スキャン中...' : '未接続',
                            style: TextStyle(
                              color: _isConnected ? Colors.green : Colors.grey,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      if (_statusMessage.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text('ステータス: $_statusMessage'),
                      ],
                      if (_errorMessage.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text(
                          'エラー: $_errorMessage',
                          style: const TextStyle(color: Colors.red),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              
              const SizedBox(height: 20),
              
              // 接続ボタン
              if (!_isConnected)
                ElevatedButton(
                  onPressed: _isScanning ? null : _scanForDevice,
                  child: Text(_isScanning ? 'スキャン中...' : '接続'),
                )
              else
                ElevatedButton(
                  onPressed: _disconnect,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                  ),
                  child: const Text('切断'),
                ),
              
              const SizedBox(height: 20),
              
              // 制御パネル
              if (_isConnected) ...[
                // スロットル制御
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      children: [
                        Text('スロットル: $_throttle%'),
                        const SizedBox(height: 10),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                          children: [
                            ElevatedButton(
                              onPressed: _throttle < 100 
                                ? () => _sendCommand(throttle: _throttle + 10)
                                : null,
                              child: const Text('▲ +10%'),
                            ),
                            ElevatedButton(
                              onPressed: _throttle > 0
                                ? () => _sendCommand(throttle: _throttle - 10)
                                : null,
                              child: const Text('▼ -10%'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                
                const SizedBox(height: 20),
                
                // 方向制御
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      children: [
                        const Text('方向制御'),
                        const SizedBox(height: 10),
                        Column(
                          children: [
                            ElevatedButton(
                              onPressed: () => _sendCommand(pitch: 10),
                              child: const Text('前進'),
                            ),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                              children: [
                                ElevatedButton(
                                  onPressed: () => _sendCommand(roll: -10),
                                  child: const Text('左'),
                                ),
                                const SizedBox(width: 60),
                                ElevatedButton(
                                  onPressed: () => _sendCommand(roll: 10),
                                  child: const Text('右'),
                                ),
                              ],
                            ),
                            ElevatedButton(
                              onPressed: () => _sendCommand(pitch: -10),
                              child: const Text('後退'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                
                const SizedBox(height: 20),
                
                // 回転制御
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    ElevatedButton(
                      onPressed: () => _sendCommand(yaw: -10),
                      child: const Text('↺ 左回転'),
                    ),
                    ElevatedButton(
                      onPressed: () => _sendCommand(yaw: 10),
                      child: const Text('↻ 右回転'),
                    ),
                  ],
                ),
                
                const SizedBox(height: 20),
                
                // 緊急停止ボタン
                ElevatedButton(
                  onPressed: _emergencyStop,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 40,
                      vertical: 20,
                    ),
                  ),
                  child: const Text(
                    '緊急停止',
                    style: TextStyle(fontSize: 18),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}