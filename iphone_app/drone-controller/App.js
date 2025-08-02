import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
  TextInput,
  SafeAreaView,
  Platform
} from 'react-native';
import BleService from './src/services/BleService';

export default function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [devices, setDevices] = useState([]);
  const [status, setStatus] = useState('');
  const [selectedDevice, setSelectedDevice] = useState(null);
  
  // PIDパラメータ
  const [rollKp, setRollKp] = useState('2.0');
  const [rollKi, setRollKi] = useState('0.0');
  const [rollKd, setRollKd] = useState('2.0');
  const [pitchKp, setPitchKp] = useState('2.0');
  const [pitchKi, setPitchKi] = useState('0.0');
  const [pitchKd, setPitchKd] = useState('2.0');
  const [yawKp, setYawKp] = useState('3.0');
  const [yawKi, setYawKi] = useState('0.1');
  const [yawKd, setYawKd] = useState('0.8');

  useEffect(() => {
    // ステータス更新のコールバック設定
    BleService.onStatusUpdate((statusMessage) => {
      setStatus(statusMessage);
    });
  }, []);

  const scanForDevices = async () => {
    try {
      setIsScanning(true);
      setDevices([]);
      
      await BleService.scanForDevices((device) => {
        setDevices(prev => {
          const exists = prev.find(d => d.id === device.id);
          if (!exists) {
            return [...prev, device];
          }
          return prev;
        });
      });

      // 5秒後にスキャン停止
      setTimeout(() => {
        BleService.stopScan();
        setIsScanning(false);
      }, 5000);
    } catch (error) {
      Alert.alert('エラー', 'スキャンに失敗しました: ' + error.message);
      setIsScanning(false);
    }
  };

  const connectToDevice = async (device) => {
    try {
      await BleService.connectToDevice(device.id);
      setIsConnected(true);
      setSelectedDevice(device);
      Alert.alert('成功', 'デバイスに接続しました');
    } catch (error) {
      Alert.alert('エラー', '接続に失敗しました: ' + error.message);
    }
  };

  const disconnect = async () => {
    try {
      await BleService.disconnect();
      setIsConnected(false);
      setSelectedDevice(null);
      setStatus('');
    } catch (error) {
      Alert.alert('エラー', '切断に失敗しました: ' + error.message);
    }
  };

  const sendCommand = async (command) => {
    try {
      await BleService.sendCommand(command);
    } catch (error) {
      Alert.alert('エラー', 'コマンド送信に失敗しました: ' + error.message);
    }
  };

  const setPIDParams = async (axis) => {
    let kp, ki, kd;
    
    switch(axis) {
      case 'ROLL':
        kp = rollKp;
        ki = rollKi;
        kd = rollKd;
        break;
      case 'PITCH':
        kp = pitchKp;
        ki = pitchKi;
        kd = pitchKd;
        break;
      case 'YAW':
        kp = yawKp;
        ki = yawKi;
        kd = yawKd;
        break;
    }
    
    const command = `PID_${axis} ${kp} ${ki} ${kd}`;
    await sendCommand(command);
    Alert.alert('設定完了', `${axis}のPIDパラメータを設定しました`);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <Text style={styles.title}>ドローンコントローラー</Text>
        
        {/* 接続状態 */}
        <View style={styles.statusContainer}>
          <Text style={styles.statusText}>
            {isConnected ? '接続済み' : '未接続'}
          </Text>
          {selectedDevice && (
            <Text style={styles.deviceText}>
              デバイス: {selectedDevice.name}
            </Text>
          )}
          {status !== '' && (
            <Text style={styles.statusMessage}>
              ステータス: {status}
            </Text>
          )}
        </View>

        {/* 接続/切断ボタン */}
        {!isConnected ? (
          <View>
            <TouchableOpacity
              style={[styles.button, styles.connectButton]}
              onPress={scanForDevices}
              disabled={isScanning}
            >
              {isScanning ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text style={styles.buttonText}>デバイスをスキャン</Text>
              )}
            </TouchableOpacity>

            {/* デバイスリスト */}
            {devices.map((device) => (
              <TouchableOpacity
                key={device.id}
                style={styles.deviceItem}
                onPress={() => connectToDevice(device)}
              >
                <Text>{device.name || device.id}</Text>
              </TouchableOpacity>
            ))}
          </View>
        ) : (
          <TouchableOpacity
            style={[styles.button, styles.disconnectButton]}
            onPress={disconnect}
          >
            <Text style={styles.buttonText}>切断</Text>
          </TouchableOpacity>
        )}

        {isConnected && (
          <>
            {/* 起動/停止ボタン */}
            <View style={styles.controlSection}>
              <Text style={styles.sectionTitle}>起動制御</Text>
              <View style={styles.buttonRow}>
                <TouchableOpacity
                  style={[styles.button, styles.startButton]}
                  onPress={() => sendCommand('RUN')}
                >
                  <Text style={styles.buttonText}>起動</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.button, styles.stopButton]}
                  onPress={() => sendCommand('STOP')}
                >
                  <Text style={styles.buttonText}>停止</Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* 方向制御 */}
            <View style={styles.controlSection}>
              <Text style={styles.sectionTitle}>方向制御</Text>
              
              <View style={styles.directionGrid}>
                <View style={styles.directionRow}>
                  <View style={styles.emptyCell} />
                  <TouchableOpacity
                    style={[styles.button, styles.directionButton]}
                    onPress={() => sendCommand('FWD')}
                  >
                    <Text style={styles.buttonText}>前進</Text>
                  </TouchableOpacity>
                  <View style={styles.emptyCell} />
                </View>
                
                <View style={styles.directionRow}>
                  <TouchableOpacity
                    style={[styles.button, styles.directionButton]}
                    onPress={() => sendCommand('LEFT')}
                  >
                    <Text style={styles.buttonText}>左回転</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.button, styles.directionButton]}
                    onPress={() => sendCommand('PARALEL')}
                  >
                    <Text style={styles.buttonText}>並行</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.button, styles.directionButton]}
                    onPress={() => sendCommand('RIGHT')}
                  >
                    <Text style={styles.buttonText}>右回転</Text>
                  </TouchableOpacity>
                </View>
                
                <View style={styles.directionRow}>
                  <View style={styles.emptyCell} />
                  <TouchableOpacity
                    style={[styles.button, styles.directionButton]}
                    onPress={() => sendCommand('BACK')}
                  >
                    <Text style={styles.buttonText}>後退</Text>
                  </TouchableOpacity>
                  <View style={styles.emptyCell} />
                </View>
              </View>

              <View style={styles.buttonRow}>
                <TouchableOpacity
                  style={[styles.button, styles.directionButton]}
                  onPress={() => sendCommand('UP')}
                >
                  <Text style={styles.buttonText}>上昇</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.button, styles.directionButton]}
                  onPress={() => sendCommand('DOWN')}
                >
                  <Text style={styles.buttonText}>下降</Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* PID制御 */}
            <View style={styles.controlSection}>
              <Text style={styles.sectionTitle}>PID制御</Text>
              
              <View style={styles.buttonRow}>
                <TouchableOpacity
                  style={[styles.button, styles.pidButton]}
                  onPress={() => sendCommand('PID_ON')}
                >
                  <Text style={styles.buttonText}>PID ON</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.button, styles.pidButton]}
                  onPress={() => sendCommand('PID_OFF')}
                >
                  <Text style={styles.buttonText}>PID OFF</Text>
                </TouchableOpacity>
              </View>

              {/* Roll PID */}
              <View style={styles.pidRow}>
                <Text style={styles.pidLabel}>Roll:</Text>
                <TextInput
                  style={styles.pidInput}
                  value={rollKp}
                  onChangeText={setRollKp}
                  placeholder="Kp"
                  keyboardType="numeric"
                />
                <TextInput
                  style={styles.pidInput}
                  value={rollKi}
                  onChangeText={setRollKi}
                  placeholder="Ki"
                  keyboardType="numeric"
                />
                <TextInput
                  style={styles.pidInput}
                  value={rollKd}
                  onChangeText={setRollKd}
                  placeholder="Kd"
                  keyboardType="numeric"
                />
                <TouchableOpacity
                  style={[styles.button, styles.pidSetButton]}
                  onPress={() => setPIDParams('ROLL')}
                >
                  <Text style={styles.buttonText}>設定</Text>
                </TouchableOpacity>
              </View>

              {/* Pitch PID */}
              <View style={styles.pidRow}>
                <Text style={styles.pidLabel}>Pitch:</Text>
                <TextInput
                  style={styles.pidInput}
                  value={pitchKp}
                  onChangeText={setPitchKp}
                  placeholder="Kp"
                  keyboardType="numeric"
                />
                <TextInput
                  style={styles.pidInput}
                  value={pitchKi}
                  onChangeText={setPitchKi}
                  placeholder="Ki"
                  keyboardType="numeric"
                />
                <TextInput
                  style={styles.pidInput}
                  value={pitchKd}
                  onChangeText={setPitchKd}
                  placeholder="Kd"
                  keyboardType="numeric"
                />
                <TouchableOpacity
                  style={[styles.button, styles.pidSetButton]}
                  onPress={() => setPIDParams('PITCH')}
                >
                  <Text style={styles.buttonText}>設定</Text>
                </TouchableOpacity>
              </View>

              {/* Yaw PID */}
              <View style={styles.pidRow}>
                <Text style={styles.pidLabel}>Yaw:</Text>
                <TextInput
                  style={styles.pidInput}
                  value={yawKp}
                  onChangeText={setYawKp}
                  placeholder="Kp"
                  keyboardType="numeric"
                />
                <TextInput
                  style={styles.pidInput}
                  value={yawKi}
                  onChangeText={setYawKi}
                  placeholder="Ki"
                  keyboardType="numeric"
                />
                <TextInput
                  style={styles.pidInput}
                  value={yawKd}
                  onChangeText={setYawKd}
                  placeholder="Kd"
                  keyboardType="numeric"
                />
                <TouchableOpacity
                  style={[styles.button, styles.pidSetButton]}
                  onPress={() => setPIDParams('YAW')}
                >
                  <Text style={styles.buttonText}>設定</Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* 緊急停止 */}
            <TouchableOpacity
              style={[styles.button, styles.emergencyButton]}
              onPress={() => sendCommand('STOP')}
            >
              <Text style={[styles.buttonText, styles.emergencyText]}>
                緊急停止
              </Text>
            </TouchableOpacity>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContainer: {
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 20,
  },
  statusContainer: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 20,
    alignItems: 'center',
  },
  statusText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  deviceText: {
    fontSize: 14,
    marginTop: 5,
  },
  statusMessage: {
    fontSize: 14,
    marginTop: 5,
    color: '#666',
  },
  button: {
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 5,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  connectButton: {
    backgroundColor: '#4CAF50',
  },
  disconnectButton: {
    backgroundColor: '#f44336',
  },
  startButton: {
    backgroundColor: '#2196F3',
    flex: 1,
    marginRight: 5,
  },
  stopButton: {
    backgroundColor: '#FF9800',
    flex: 1,
    marginLeft: 5,
  },
  directionButton: {
    backgroundColor: '#9C27B0',
    flex: 1,
    margin: 5,
  },
  pidButton: {
    backgroundColor: '#00BCD4',
    flex: 1,
    marginHorizontal: 5,
  },
  pidSetButton: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 20,
    marginLeft: 10,
  },
  emergencyButton: {
    backgroundColor: '#f44336',
    marginTop: 30,
    paddingVertical: 20,
  },
  emergencyText: {
    fontSize: 20,
  },
  controlSection: {
    marginVertical: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  deviceItem: {
    backgroundColor: 'white',
    padding: 15,
    marginVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  directionGrid: {
    alignItems: 'center',
    marginVertical: 10,
  },
  directionRow: {
    flexDirection: 'row',
    justifyContent: 'center',
  },
  emptyCell: {
    flex: 1,
    margin: 5,
  },
  pidRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 5,
  },
  pidLabel: {
    width: 50,
    fontSize: 16,
  },
  pidInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    padding: 8,
    marginHorizontal: 5,
    backgroundColor: 'white',
  },
});