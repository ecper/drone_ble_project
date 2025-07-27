import React, { useState, useEffect, useRef } from "react";
import {
	StyleSheet,
	Text,
	View,
	Alert,
	ScrollView,
	SafeAreaView,
} from "react-native";
import { StatusBar } from "expo-status-bar";

// プラットフォーム別のインポート
import { BleService } from "./src/services";
import { State } from "./src/services/BleServiceTypes";
import { ConnectionButton } from "./src/components/ConnectionButton";
import { DroneControl } from "./src/components/DroneControl";
import { StatusDisplay } from "./src/components/StatusDisplay";
import { BleConnectionState, DroneCommand } from "./src/types/ble.types";

export default function App() {
	const [bleState, setBleState] = useState<State>(State.Unknown);
	const [connectionState, setConnectionState] =
		useState<BleConnectionState>("disconnected");
	const [statusMessage, setStatusMessage] = useState<string>("");
	const [errorMessage, setErrorMessage] = useState<string>("");
	const [throttle, setThrottle] = useState<number>(0);

	const bleService = useRef<BleService>(new BleService());
	const statusUnsubscribe = useRef<(() => void) | null>(null);

	useEffect(() => {
		// 権限リクエスト
		requestPermissions();

		// BLE状態の監視
		const unsubscribe = bleService.current.onStateChange(setBleState);

		// クリーンアップ
		return () => {
			unsubscribe();
			if (statusUnsubscribe.current) {
				statusUnsubscribe.current();
			}
			bleService.current.destroy();
		};
	}, []);

	// 権限リクエスト（iOS用）
	const requestPermissions = async (): Promise<void> => {
		// iOSではInfo.plistで設定済みなので、特別な処理は不要
		console.log("iOS: Bluetooth permissions configured in Info.plist");
	};

	// 接続処理
	const handleConnect = async (): Promise<void> => {
		if (bleState !== State.PoweredOn) {
			Alert.alert("エラー", "Bluetoothを有効にしてください");
			return;
		}

		try {
			setConnectionState("scanning");
			setErrorMessage("");

			// デバイススキャン
			const device = await bleService.current.scanForDevice();

			// 接続
			setConnectionState("connecting");
			await bleService.current.connectToDevice(device);

			// ステータス監視開始
			statusUnsubscribe.current = await bleService.current.monitorStatus(
				(status) => {
					setStatusMessage(status);
				},
			);

			setConnectionState("connected");
			setStatusMessage("接続完了");
		} catch (error) {
			setConnectionState("error");
			setErrorMessage(
				error instanceof Error ? error.message : "接続エラー",
			);
			Alert.alert(
				"接続エラー",
				error instanceof Error ? error.message : "不明なエラー",
			);
		}
	};

	// 切断処理
	const handleDisconnect = async (): Promise<void> => {
		try {
			if (statusUnsubscribe.current) {
				statusUnsubscribe.current();
				statusUnsubscribe.current = null;
			}

			await bleService.current.disconnect();
			setConnectionState("disconnected");
			setStatusMessage("");
			setThrottle(0);
		} catch (error) {
			setErrorMessage(
				error instanceof Error ? error.message : "切断エラー",
			);
		}
	};

	// コマンド送信
	const handleCommand = async (
		command: Partial<DroneCommand>,
	): Promise<void> => {
		if (connectionState !== "connected") {
			Alert.alert("エラー", "デバイスが接続されていません");
			return;
		}

		try {
			const fullCommand: DroneCommand = {
				throttle: command.throttle ?? throttle,
				pitch: command.pitch ?? 0,
				roll: command.roll ?? 0,
				yaw: command.yaw ?? 0,
			};

			await bleService.current.sendDroneCommand(fullCommand);

			// スロットル値を更新
			if (command.throttle !== undefined) {
				setThrottle(command.throttle);
			}
		} catch (error) {
			setErrorMessage(
				error instanceof Error ? error.message : "送信エラー",
			);
			Alert.alert(
				"送信エラー",
				error instanceof Error ? error.message : "不明なエラー",
			);
		}
	};

	// 停止
	const handleStop = async (): Promise<void> => {
		try {
			await bleService.current.sendStopCommand();
			setThrottle(0);
			setStatusMessage("緊急停止");
		} catch (error) {
			setErrorMessage(
				error instanceof Error ? error.message : "停止エラー",
			);
		}
	};

	return (
		<SafeAreaView style={styles.container}>
			<StatusBar style="auto" />
			<ScrollView contentContainerStyle={styles.scrollView}>
				<Text style={styles.title}>ドローンコントローラー</Text>

				{/* ステータス表示 */}
				<StatusDisplay
					bleState={bleState}
					connectionState={connectionState}
					statusMessage={statusMessage}
					errorMessage={errorMessage}
				/>

				{/* 接続ボタン */}
				<View style={styles.connectionContainer}>
					<ConnectionButton
						connectionState={connectionState}
						onConnect={handleConnect}
						onDisconnect={handleDisconnect}
					/>
				</View>

				{/* 制御パネル */}
				{connectionState === "connected" && (
					<View style={styles.controlPanel}>
						<DroneControl
							throttle={throttle}
							onCommand={handleCommand}
							onStop={handleStop}
						/>
					</View>
				)}
			</ScrollView>
		</SafeAreaView>
	);
}

const styles = StyleSheet.create({
	container: {
		flex: 1,
		backgroundColor: "#f5f5f5",
	},
	scrollView: {
		flexGrow: 1,
		padding: 20,
	},
	title: {
		fontSize: 28,
		fontWeight: "bold",
		textAlign: "center",
		marginBottom: 30,
		color: "#333",
	},
	connectionContainer: {
		alignItems: "center",
		marginBottom: 30,
	},
	controlPanel: {
		backgroundColor: "white",
		padding: 20,
		borderRadius: 15,
		shadowColor: "#000",
		shadowOffset: { width: 0, height: 2 },
		shadowOpacity: 0.1,
		shadowRadius: 4,
		elevation: 3,
	},
});
