import React from 'react';
import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { BleConnectionState } from '../types/ble.types';

interface ConnectionButtonProps {
  connectionState: BleConnectionState;
  onConnect: () => void;
  onDisconnect: () => void;
}

export const ConnectionButton: React.FC<ConnectionButtonProps> = ({
  connectionState,
  onConnect,
  onDisconnect,
}) => {
  const getButtonStyle = (): ViewStyle => {
    switch (connectionState) {
      case 'connected':
        return styles.disconnectButton;
      case 'scanning':
      case 'connecting':
        return styles.connectingButton;
      default:
        return styles.connectButton;
    }
  };

  const renderContent = () => {
    switch (connectionState) {
      case 'scanning':
        return (
          <>
            <ActivityIndicator color="white" style={styles.spinner} />
            <Text style={styles.buttonText}>スキャン中...</Text>
          </>
        );
      case 'connecting':
        return (
          <>
            <ActivityIndicator color="white" style={styles.spinner} />
            <Text style={styles.buttonText}>接続中...</Text>
          </>
        );
      case 'connected':
        return <Text style={styles.buttonText}>切断</Text>;
      default:
        return <Text style={styles.buttonText}>接続</Text>;
    }
  };

  const handlePress = () => {
    if (connectionState === 'connected') {
      onDisconnect();
    } else if (connectionState === 'disconnected') {
      onConnect();
    }
  };

  const isDisabled = connectionState === 'scanning' || connectionState === 'connecting';

  return (
    <TouchableOpacity
      style={[styles.button, getButtonStyle()]}
      onPress={handlePress}
      disabled={isDisabled}
    >
      {renderContent()}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 10,
    minWidth: 200,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  connectButton: {
    backgroundColor: '#4CAF50',
  },
  disconnectButton: {
    backgroundColor: '#f44336',
  },
  connectingButton: {
    backgroundColor: '#2196F3',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
  spinner: {
    marginRight: 10,
  },
});