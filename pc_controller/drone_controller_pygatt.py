#!/usr/bin/env python3
"""
ドローンコントローラー - pygatt版
gatttoolをバックエンドとして使用
"""

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import pygatt

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BLE設定
DEVICE_ADDRESS = "D8:3A:DD:EE:48:0D"
COMMAND_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
STATUS_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


class DroneController:
    def __init__(self):
        self.adapter = None
        self.device = None
        self.connected = False
        self.throttle = 0
        self.status_queue = queue.Queue()

    def connect_to_device(self):
        """デバイスに接続"""
        try:
            logger.info("BLEアダプタを初期化中...")
            self.adapter = pygatt.GATTToolBackend()
            self.adapter.start(reset_on_start=False)

            logger.info(f"デバイス {DEVICE_ADDRESS} に接続中...")
            self.device = self.adapter.connect(DEVICE_ADDRESS)
            self.connected = True
            logger.info("接続成功！")

            # 通知を有効化
            try:
                self.device.subscribe(STATUS_UUID, callback=self.notification_handler)
                logger.info("通知を有効化しました")
            except Exception as e:
                logger.warning(f"通知有効化エラー: {e}")

            return True

        except Exception as e:
            logger.error(f"接続エラー: {e}")
            self.connected = False
            if self.adapter:
                try:
                    self.adapter.stop()
                except:
                    pass
            return False

    def notification_handler(self, handle, data):
        """BLE通知ハンドラー"""
        try:
            status_message = data.decode("utf-8")
            logger.info(f"ステータス受信: {status_message}")
            self.status_queue.put(status_message)
        except Exception as e:
            logger.error(f"通知処理エラー: {e}")

    def send_run_command(self):
        """起動/停止コマンド送信"""
        if not self.connected or not self.device:
            logger.warning("未接続のためコマンドを送信できません")
            return False

        try:
            command = "RUN"
            self.device.char_write(
                COMMAND_UUID, command.encode(), wait_for_response=False
            )
            logger.info(f"コマンド送信: {command}")
            return True
        except Exception as e:
            logger.error(f"送信エラー: {e}")
            return False

    def send_stop_command(self):
        """停止コマンド送信"""
        if not self.connected or not self.device:
            logger.warning("未接続のためコマンドを送信できません")
            return False

        try:
            command = "STOP"
            self.device.char_write(
                COMMAND_UUID, command.encode(), wait_for_response=False
            )
            logger.info(f"コマンド送信: {command}")
            return True
        except Exception as e:
            logger.error(f"送信エラー: {e}")
            return False

    def send_command(self, throttle=None, pitch=0, roll=0, yaw=0):
        """コマンド送信"""
        if not self.connected or not self.device:
            logger.warning("未接続のためコマンドを送信できません")
            return False

        try:
            if throttle is not None:
                self.throttle = throttle

            command = f"T{self.throttle},P{pitch},R{roll},Y{yaw}"
            self.device.char_write(
                COMMAND_UUID, command.encode(), wait_for_response=False
            )
            logger.info(f"コマンド送信: {command}")
            return True

        except Exception as e:
            logger.error(f"送信エラー: {e}")
            return False

    def disconnect(self):
        """切断"""
        if self.adapter:
            try:
                self.adapter.stop()
            except:
                pass
        self.connected = False
        logger.info("切断しました")


class DroneControllerGUI:
    def __init__(self):
        self.controller = DroneController()
        self.root = tk.Tk()
        self.root.title("ドローンコントローラー (pygatt)")
        self.root.geometry("600x700")

        self.setup_ui()
        self.update_status()

    def setup_ui(self):
        """UI構築"""
        # ヘッダー
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)

        ttk.Label(
            header_frame, text="ドローンコントローラー", font=("Arial", 20, "bold")
        ).pack()

        # 接続状態
        self.status_frame = ttk.LabelFrame(self.root, text="接続状態", padding="10")
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.connection_label = ttk.Label(
            self.status_frame, text="未接続", font=("Arial", 12)
        )
        self.connection_label.pack()

        self.status_label = ttk.Label(self.status_frame, text="", font=("Arial", 10))
        self.status_label.pack()

        # 接続ボタン
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack()

        self.connect_button = ttk.Button(
            button_frame, text="接続", command=self.connect_device, width=20
        )
        self.connect_button.pack(side=tk.LEFT, padx=5)

        self.disconnect_button = ttk.Button(
            button_frame,
            text="切断",
            command=self.disconnect_device,
            state=tk.DISABLED,
            width=20,
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=5)

        # スロットル制御
        throttle_frame = ttk.LabelFrame(self.root, text="スロットル制御", padding="10")
        throttle_frame.pack(fill=tk.X, padx=10, pady=10)

        self.throttle_var = tk.IntVar(value=0)
        self.throttle_label = ttk.Label(throttle_frame, text="0%", font=("Arial", 16))
        self.throttle_label.pack()

        self.throttle_scale = ttk.Scale(
            throttle_frame,
            from_=0,
            to=100,
            variable=self.throttle_var,
            orient=tk.HORIZONTAL,
            command=self.update_throttle,
        )
        self.throttle_scale.pack(fill=tk.X, pady=10)

        # 起動ボタン
        start_button_frame = ttk.Frame(throttle_frame)
        start_button_frame.pack()

        ttk.Button(
            start_button_frame,
            text="起動",
            command=self.start_drone,
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            start_button_frame,
            text="停止",
            command=self.stop_drone,
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        # 方向制御
        direction_frame = ttk.LabelFrame(self.root, text="方向制御", padding="10")
        direction_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 方向ボタン
        ttk.Button(
            direction_frame,
            text="前進\n↑",
            width=10,
            command=lambda: self.send_direction_command(pitch=10),
        ).pack(pady=5)

        middle_frame = ttk.Frame(direction_frame)
        middle_frame.pack(pady=10)

        ttk.Button(
            middle_frame,
            text="左\n←",
            width=10,
            command=lambda: self.send_direction_command(roll=-10),
        ).pack(side=tk.LEFT, padx=20)
        ttk.Button(
            middle_frame,
            text="右\n→",
            width=10,
            command=lambda: self.send_direction_command(roll=10),
        ).pack(side=tk.LEFT, padx=20)

        ttk.Button(
            direction_frame,
            text="後退\n↓",
            width=10,
            command=lambda: self.send_direction_command(pitch=-10),
        ).pack(pady=5)

        # 回転制御
        rotation_frame = ttk.LabelFrame(self.root, text="回転制御", padding="10")
        rotation_frame.pack(fill=tk.X, padx=10, pady=10)

        rotation_button_frame = ttk.Frame(rotation_frame)
        rotation_button_frame.pack()

        ttk.Button(
            rotation_button_frame,
            text="↺ 左回転",
            width=15,
            command=lambda: self.send_direction_command(yaw=-10),
        ).pack(side=tk.LEFT, padx=10)
        ttk.Button(
            rotation_button_frame,
            text="↻ 右回転",
            width=15,
            command=lambda: self.send_direction_command(yaw=10),
        ).pack(side=tk.LEFT, padx=10)

        # 緊急停止
        ttk.Button(
            self.root,
            text="緊急停止",
            command=self.emergency_stop,
            style="Emergency.TButton",
        ).pack(pady=20)

        # スタイル設定
        style = ttk.Style()
        style.configure(
            "Emergency.TButton", foreground="red", font=("Arial", 16, "bold")
        )

    def connect_device(self):
        """デバイスに接続"""
        self.connect_button.config(state=tk.DISABLED, text="接続中...")

        # 別スレッドで接続
        def _connect():
            success = self.controller.connect_to_device()
            self.root.after(0, self.on_connection_result, success)

        threading.Thread(target=_connect, daemon=True).start()

    def disconnect_device(self):
        """デバイスから切断"""
        self.controller.disconnect()
        self.on_disconnected()

    def start_drone(self):
        """ドローンを起動"""
        self.controller.send_run_command()

    def stop_drone(self):
        """ドローンを停止"""
        self.controller.send_stop_command()

    def send_direction_command(self, pitch=0, roll=0, yaw=0):
        """方向コマンド送信"""
        if not self.controller.connected:
            messagebox.showwarning("警告", "デバイスが接続されていません")
            return

        self.controller.send_command(pitch=pitch, roll=roll, yaw=yaw)

    def update_throttle(self, value):
        """スロットル更新"""
        throttle = int(float(value))
        self.throttle_label.config(text=f"{throttle}%")

        if self.controller.connected:
            self.controller.send_command(throttle=throttle)

    def emergency_stop(self):
        """緊急停止"""
        self.throttle_var.set(0)
        if self.controller.connected:
            self.controller.send_command(throttle=0)
            messagebox.showinfo("緊急停止", "モーターを停止しました")

    def on_connection_result(self, success):
        """接続結果処理"""
        if success:
            self.connection_label.config(text="接続済み", foreground="green")
            self.connect_button.config(state=tk.DISABLED, text="接続")
            self.disconnect_button.config(state=tk.NORMAL)
        else:
            self.connection_label.config(text="接続失敗", foreground="red")
            self.connect_button.config(state=tk.NORMAL, text="接続")
            messagebox.showerror("エラー", "デバイスへの接続に失敗しました")

    def on_disconnected(self):
        """切断時処理"""
        self.connection_label.config(text="未接続", foreground="black")
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.throttle_var.set(0)

    def update_status(self):
        """ステータス更新"""
        try:
            while not self.controller.status_queue.empty():
                status = self.controller.status_queue.get_nowait()
                self.status_label.config(text=f"ステータス: {status}")
        except queue.Empty:
            pass

        self.root.after(100, self.update_status)

    def run(self):
        """アプリケーション実行"""
        try:
            self.root.mainloop()
        finally:
            self.controller.disconnect()


def main():
    """メイン関数"""
    # pygattがインストールされているか確認
    try:
        import pygatt
    except ImportError:
        print("pygattがインストールされていません。")
        print("以下のコマンドでインストールしてください：")
        print("  pip install pygatt")
        return

    app = DroneControllerGUI()
    app.run()


if __name__ == "__main__":
    main()
