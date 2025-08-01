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
DEVICE_ADDRESS = "2C:CF:67:F5:0B:E0"
COMMAND_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
STATUS_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


class DroneController:
    def __init__(self):
        self.adapter = None
        self.device = None
        self.connected = False
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
            self.send_command(command)
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
            self.send_command(command)
            logger.info(f"コマンド送信: {command}")
            return True
        except Exception as e:
            logger.error(f"送信エラー: {e}")
            return False

    def send_command(self, command: str = None):
        """コマンド送信"""
        if not self.connected or not self.device:
            logger.warning("未接続のためコマンドを送信できません")
            return False

        try:
            command = f"{command}"
            self.device.char_write(
                COMMAND_UUID, command.encode(), wait_for_response=False
            )
            logger.info(f"コマンド送信: {command}")
            return True

        except Exception as e:
            logger.error(f"送信エラー: {e}")
            return False
    
    def send_parameter(self, param_name, value):
        """パラメータ設定コマンド送信"""
        if not self.connected or not self.device:
            logger.warning("未接続のためパラメータを送信できません")
            return False
        
        try:
            command = f"SET:{param_name}={value}"
            self.device.char_write(COMMAND_UUID, command.encode(), wait_for_response=False)
            logger.info(f"パラメータ送信: {command}")
            return True
            
        except Exception as e:
            logger.error(f"パラメータ送信エラー: {e}")
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
        self.root.geometry("700x900")

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

        # 起動ボタン
        start_button_frame = ttk.LabelFrame(self.root, text="起動ボタン", padding="10")
        start_button_frame.pack(fill=tk.X, padx=10, pady=10)

        # 起動ボタン
        start_button_frame = ttk.Frame(start_button_frame)
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

        # ESCテスト・調整フレーム
        esc_test_frame = ttk.LabelFrame(self.root, text="ESCテスト・調整", padding="5")
        esc_test_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # ESC個別テストボタン
        test_buttons_frame = ttk.Frame(esc_test_frame)
        test_buttons_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(test_buttons_frame, text="個別テスト:").pack(side=tk.LEFT, padx=5)
        
        for i in range(4):
            ttk.Button(
                test_buttons_frame,
                text=f"TEST{i}",
                command=lambda x=i: self.send_test_command(x),
                width=8
            ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            test_buttons_frame,
            text="STATUS",
            command=lambda: self.send_command("STATUS"),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        # ESCオフセット調整
        offset_frame = ttk.Frame(esc_test_frame)
        offset_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(offset_frame, text="オフセット調整:").pack(side=tk.LEFT, padx=5)
        
        # ESC選択とオフセット値入力
        self.selected_esc = tk.IntVar(value=0)
        self.offset_value = tk.IntVar(value=0)
        
        esc_select_frame = ttk.Frame(offset_frame)
        esc_select_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(esc_select_frame, text="ESC:").pack(side=tk.LEFT)
        for i in range(4):
            ttk.Radiobutton(
                esc_select_frame,
                text=str(i),
                variable=self.selected_esc,
                value=i
            ).pack(side=tk.LEFT)
        
        ttk.Label(offset_frame, text="値:").pack(side=tk.LEFT, padx=(10,2))
        offset_entry = ttk.Entry(offset_frame, textvariable=self.offset_value, width=6)
        offset_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            offset_frame,
            text="設定",
            command=self.send_offset_command,
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        # 方向制御
        direction_frame = ttk.LabelFrame(self.root, text="方向制御", padding="10")
        direction_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # メインレイアウト（左右分割）
        main_layout_frame = ttk.Frame(direction_frame)
        main_layout_frame.pack(fill=tk.BOTH, expand=True)

        # 左側フレーム（上昇・左回転・右回転・下降）
        left_frame = ttk.LabelFrame(main_layout_frame, text="上下・回転", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # 上昇ボタン
        ttk.Button(
            left_frame,
            text="上昇",
            width=10,
            command=lambda: self.send_direction_command("UP"),
        ).pack(pady=5)

        # 左右回転ボタン
        rotation_frame = ttk.Frame(left_frame)
        rotation_frame.pack(pady=10)

        ttk.Button(
            rotation_frame,
            text="左回転",
            width=10,
            command=lambda: self.send_direction_command("LEFT"),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            rotation_frame,
            text="右回転",
            width=10,
            command=lambda: self.send_direction_command("RIGHT"),
        ).pack(side=tk.LEFT, padx=5)

        # 下降ボタン
        ttk.Button(
            left_frame,
            text="下降",
            width=10,
            command=lambda: self.send_direction_command("DOWN"),
        ).pack(pady=5)

        # 右側フレーム（前進・後退）
        right_frame = ttk.LabelFrame(main_layout_frame, text="前後移動", padding="5")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # 前後移動ボタンを縦に配置
        ttk.Button(
            right_frame,
            text="前進",
            width=10,
            command=lambda: self.send_direction_command("FWD"),
        ).pack(pady=20)
        ttk.Button(
            right_frame,
            text="並行",
            width=10,
            command=lambda: self.send_direction_command("PARALEL"),
        ).pack(pady=20) 
        ttk.Button(
            right_frame,
            text="後退",
            width=10,
            command=lambda: self.send_direction_command("BACK"),
        ).pack(pady=20)
        

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


    def send_direction_command(self, command: str = None):
        """方向コマンド送信"""
        if not self.controller.connected:
            messagebox.showwarning("警告", "デバイスが接続されていません")
            return

        self.controller.send_command(command)

    def send_test_command(self, esc_num):
        """ESC個別テストコマンド送信"""
        if not self.controller.connected:
            messagebox.showwarning("警告", "デバイスが接続されていません")
            return
        
        command = f"TEST{esc_num}"
        self.controller.send_command(command)
        messagebox.showinfo("テスト", f"ESC{esc_num}の個別テストを開始しました")

    def send_offset_command(self):
        """ESCオフセット調整コマンド送信"""
        if not self.controller.connected:
            messagebox.showwarning("警告", "デバイスが接続されていません")
            return
        
        esc_num = self.selected_esc.get()
        offset_val = self.offset_value.get()
        
        # 範囲チェック
        if offset_val < -200 or offset_val > 200:
            messagebox.showerror("エラー", "オフセット値は-200から200の範囲で入力してください")
            return
        
        command = f"OFFSET{esc_num} {offset_val}"
        self.controller.send_command(command)
        messagebox.showinfo("設定完了", f"ESC{esc_num}のオフセットを{offset_val}に設定しました")

    def emergency_stop(self):
        """緊急停止"""
        if self.controller.connected:
            self.controller.send_stop_command()
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
