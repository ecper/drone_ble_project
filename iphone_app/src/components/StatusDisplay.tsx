import React from 'react';
import {
  View,
  Text,
  StyleSheet,
} from 'react-native';
import { State } from '../services/BleServiceTypes';
import { BleConnectionState } from '../types/ble.types';

interface StatusDisplayProps {
  bleState: State;
  connectionState: BleConnectionState;
  statusMessage: string;
  errorMessage?: string;
}

export const StatusDisplay: React.FC<StatusDisplayProps> = ({
  bleState,
  connectionState,
  statusMessage,
  errorMessage,
}) => {
  const getConnectionStateText = (): string => {
    switch (connectionState) {
      case 'connected':
        return '接続済み';
      case 'connecting':
        return '接続中...';
      case 'scanning':
        return 'スキャン中...';
      case 'error':
        return 'エラー';
      default:
        return '未接続';
    }
  };

  const getConnectionStateColor = (): string => {
    switch (connectionState) {
      case 'connected':
        return '#4CAF50';
      case 'error':
        return '#f44336';
      default:
        return '#666';
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.statusRow}>
        <Text style={styles.label}>Bluetooth:</Text>
        <Text style={[
          styles.value,
          { color: bleState === State.PoweredOn ? '#4CAF50' : '#f44336' }
        ]}>
          {bleState}
        </Text>
      </View>
      
      <View style={styles.statusRow}>
        <Text style={styles.label}>接続状態:</Text>
        <Text style={[
          styles.value,
          { color: getConnectionStateColor() }
        ]}>
          {getConnectionStateText()}
        </Text>
      </View>
      
      {statusMessage !== '' && (
        <View style={styles.statusRow}>
          <Text style={styles.label}>ステータス:</Text>
          <Text style={styles.value}>{statusMessage}</Text>
        </View>
      )}
      
      {errorMessage && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{errorMessage}</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  label: {
    fontSize: 16,
    color: '#666',
    fontWeight: '500',
  },
  value: {
    fontSize: 16,
    fontWeight: '600',
  },
  errorContainer: {
    marginTop: 10,
    padding: 10,
    backgroundColor: '#ffebee',
    borderRadius: 5,
  },
  errorText: {
    color: '#c62828',
    fontSize: 14,
  },
});