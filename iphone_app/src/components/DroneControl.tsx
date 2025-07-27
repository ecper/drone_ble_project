import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { DroneCommand } from '../types/ble.types';

interface DroneControlProps {
  throttle: number;
  onCommand: (command: Partial<DroneCommand>) => void;
  onStop: () => void;
}

export const DroneControl: React.FC<DroneControlProps> = ({
  throttle,
  onCommand,
  onStop,
}) => {
  // スロットル制御
  const handleThrottleUp = () => {
    const newThrottle = Math.min(throttle + 10, 100);
    onCommand({ throttle: newThrottle, pitch: 0, roll: 0, yaw: 0 });
  };

  const handleThrottleDown = () => {
    const newThrottle = Math.max(throttle - 10, 0);
    onCommand({ throttle: newThrottle, pitch: 0, roll: 0, yaw: 0 });
  };

  // 方向制御
  const handleDirection = (pitch: number, roll: number) => {
    onCommand({ throttle, pitch, roll, yaw: 0 });
  };

  // 回転制御
  const handleRotation = (yaw: number) => {
    onCommand({ throttle, pitch: 0, roll: 0, yaw });
  };

  return (
    <View style={styles.container}>
      {/* スロットル制御 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>高度制御</Text>
        <View style={styles.throttleContainer}>
          <TouchableOpacity
            style={[styles.button, styles.controlButton]}
            onPress={handleThrottleUp}
          >
            <Text style={styles.buttonText}>↑ 上昇</Text>
          </TouchableOpacity>
          <View style={styles.throttleInfo}>
            <Text style={styles.throttleText}>{throttle}%</Text>
          </View>
          <TouchableOpacity
            style={[styles.button, styles.controlButton]}
            onPress={handleThrottleDown}
          >
            <Text style={styles.buttonText}>↓ 下降</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* 方向制御 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>方向制御</Text>
        <View style={styles.directionContainer}>
          <View style={styles.row}>
            <View style={styles.spacer} />
            <TouchableOpacity
              style={[styles.button, styles.controlButton]}
              onPress={() => handleDirection(10, 0)}
              onLongPress={() => handleDirection(20, 0)}
            >
              <Text style={styles.buttonText}>前進</Text>
            </TouchableOpacity>
            <View style={styles.spacer} />
          </View>
          
          <View style={styles.row}>
            <TouchableOpacity
              style={[styles.button, styles.controlButton]}
              onPress={() => handleDirection(0, -10)}
              onLongPress={() => handleDirection(0, -20)}
            >
              <Text style={styles.buttonText}>左</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.button, styles.stopButton]}
              onPress={onStop}
            >
              <Text style={styles.buttonText}>停止</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.button, styles.controlButton]}
              onPress={() => handleDirection(0, 10)}
              onLongPress={() => handleDirection(0, 20)}
            >
              <Text style={styles.buttonText}>右</Text>
            </TouchableOpacity>
          </View>
          
          <View style={styles.row}>
            <View style={styles.spacer} />
            <TouchableOpacity
              style={[styles.button, styles.controlButton]}
              onPress={() => handleDirection(-10, 0)}
              onLongPress={() => handleDirection(-20, 0)}
            >
              <Text style={styles.buttonText}>後退</Text>
            </TouchableOpacity>
            <View style={styles.spacer} />
          </View>
        </View>
      </View>

      {/* 回転制御 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>回転制御</Text>
        <View style={styles.rotationContainer}>
          <TouchableOpacity
            style={[styles.button, styles.controlButton]}
            onPress={() => handleRotation(-10)}
            onLongPress={() => handleRotation(-30)}
          >
            <Text style={styles.buttonText}>↺ 左回転</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.button, styles.controlButton]}
            onPress={() => handleRotation(10)}
            onLongPress={() => handleRotation(30)}
          >
            <Text style={styles.buttonText}>↻ 右回転</Text>
          </TouchableOpacity>
        </View>
      </View>

      <Text style={styles.hint}>長押しで強い動作</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10,
    textAlign: 'center',
    color: '#333',
  },
  throttleContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  throttleInfo: {
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 10,
  },
  throttleText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  directionContainer: {
    alignItems: 'center',
  },
  row: {
    flexDirection: 'row',
    marginVertical: 5,
  },
  rotationContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  button: {
    padding: 15,
    borderRadius: 10,
    minWidth: 80,
    minHeight: 80,
    alignItems: 'center',
    justifyContent: 'center',
    margin: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  controlButton: {
    backgroundColor: '#2196F3',
  },
  stopButton: {
    backgroundColor: '#FF9800',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
    textAlign: 'center',
  },
  spacer: {
    width: 90,
  },
  hint: {
    textAlign: 'center',
    color: '#666',
    marginTop: 10,
    fontSize: 14,
  },
});