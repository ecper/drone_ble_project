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
        self.root.geometry("700x1200")

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
        

        # PIDパラメータ調整フレーム
        pid_frame = ttk.LabelFrame(self.root, text="PIDパラメータ調整", padding="10")
        pid_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # PID有効/無効切り替え
        pid_toggle_frame = ttk.Frame(pid_frame)
        pid_toggle_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            pid_toggle_frame,
            text="PID ON",
            command=lambda: self.send_command("PID_ON"),
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            pid_toggle_frame,
            text="PID OFF",
            command=lambda: self.send_command("PID_OFF"),
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # Roll PIDパラメータ
        roll_frame = ttk.Frame(pid_frame)
        roll_frame.pack(fill=tk.X, pady=2)
        ttk.Label(roll_frame, text="Roll:", width=6).pack(side=tk.LEFT, padx=5)
        
        self.roll_kp = tk.DoubleVar(value=2.0)
        self.roll_ki = tk.DoubleVar(value=0.0)
        self.roll_kd = tk.DoubleVar(value=2.0)
        
        ttk.Label(roll_frame, text="Kp:").pack(side=tk.LEFT)
        ttk.Entry(roll_frame, textvariable=self.roll_kp, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(roll_frame, text="Ki:").pack(side=tk.LEFT, padx=(10,0))
        ttk.Entry(roll_frame, textvariable=self.roll_ki, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(roll_frame, text="Kd:").pack(side=tk.LEFT, padx=(10,0))
        ttk.Entry(roll_frame, textvariable=self.roll_kd, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(roll_frame, text="設定", command=lambda: self.set_pid_params("ROLL"), width=6).pack(side=tk.LEFT, padx=5)
        
        # Pitch PIDパラメータ
        pitch_frame = ttk.Frame(pid_frame)
        pitch_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pitch_frame, text="Pitch:", width=6).pack(side=tk.LEFT, padx=5)
        
        self.pitch_kp = tk.DoubleVar(value=2.0)
        self.pitch_ki = tk.DoubleVar(value=0.0)
        self.pitch_kd = tk.DoubleVar(value=2.0)
        
        ttk.Label(pitch_frame, text="Kp:").pack(side=tk.LEFT)
        ttk.Entry(pitch_frame, textvariable=self.pitch_kp, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(pitch_frame, text="Ki:").pack(side=tk.LEFT, padx=(10,0))
        ttk.Entry(pitch_frame, textvariable=self.pitch_ki, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(pitch_frame, text="Kd:").pack(side=tk.LEFT, padx=(10,0))
        ttk.Entry(pitch_frame, textvariable=self.pitch_kd, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(pitch_frame, text="設定", command=lambda: self.set_pid_params("PITCH"), width=6).pack(side=tk.LEFT, padx=5)
        
        # Yaw PIDパラメータ
        yaw_frame = ttk.Frame(pid_frame)
        yaw_frame.pack(fill=tk.X, pady=2)
        ttk.Label(yaw_frame, text="Yaw:", width=6).pack(side=tk.LEFT, padx=5)
        
        self.yaw_kp = tk.DoubleVar(value=3.0)
        self.yaw_ki = tk.DoubleVar(value=0.1)
        self.yaw_kd = tk.DoubleVar(value=0.8)
        
        ttk.Label(yaw_frame, text="Kp:").pack(side=tk.LEFT)
        ttk.Entry(yaw_frame, textvariable=self.yaw_kp, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(yaw_frame, text="Ki:").pack(side=tk.LEFT, padx=(10,0))
        ttk.Entry(yaw_frame, textvariable=self.yaw_ki, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(yaw_frame, text="Kd:").pack(side=tk.LEFT, padx=(10,0))
        ttk.Entry(yaw_frame, textvariable=self.yaw_kd, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(yaw_frame, text="設定", command=lambda: self.set_pid_params("YAW"), width=6).pack(side=tk.LEFT, padx=5)
        
        # 簡単調整ボタン
        quick_adjust_frame = ttk.LabelFrame(pid_frame, text="簡単調整", padding="5")
        quick_adjust_frame.pack(fill=tk.X, pady=5)
        
        quick_buttons_frame = ttk.Frame(quick_adjust_frame)
        quick_buttons_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(
            quick_buttons_frame,
            text="穏やか",
            command=lambda: self.send_command("PID_GENTLE"),
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            quick_buttons_frame,
            text="標準",
            command=lambda: self.send_command("PID_NORMAL"),
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            quick_buttons_frame,
            text="積極的",
            command=lambda: self.send_command("PID_AGGRESSIVE"),
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        # D項実装方法の簡単切り替え
        d_quick_frame = ttk.Frame(pid_frame)
        d_quick_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(d_quick_frame, text="D項方法:").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            d_quick_frame,
            text="ジャイロ",
            command=lambda: self.send_command("D_GYRO"),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            d_quick_frame,
            text="エラー微分",
            command=lambda: self.send_command("D_ERROR"),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        # その他のパラメータ
        other_params_frame = ttk.LabelFrame(pid_frame, text="その他のパラメータ", padding="5")
        other_params_frame.pack(fill=tk.X, pady=5)
        
        # 不感帯設定
        deadband_frame = ttk.Frame(other_params_frame)
        deadband_frame.pack(fill=tk.X, pady=2)
        ttk.Label(deadband_frame, text="角度不感帯(度):").pack(side=tk.LEFT, padx=5)
        self.angle_deadband = tk.DoubleVar(value=0.1)
        ttk.Entry(deadband_frame, textvariable=self.angle_deadband, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(deadband_frame, text="設定", command=lambda: self.set_param("DEADBAND", self.angle_deadband.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # 最小補正値設定
        min_corr_frame = ttk.Frame(other_params_frame)
        min_corr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(min_corr_frame, text="最小補正値(µs):").pack(side=tk.LEFT, padx=5)
        self.min_correction = tk.IntVar(value=30)
        ttk.Entry(min_corr_frame, textvariable=self.min_correction, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(min_corr_frame, text="設定", command=lambda: self.set_param("MIN_CORR", self.min_correction.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # 最大補正値設定
        max_corr_frame = ttk.Frame(other_params_frame)
        max_corr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_corr_frame, text="最大補正値(µs):").pack(side=tk.LEFT, padx=5)
        self.max_correction = tk.IntVar(value=100)
        ttk.Entry(max_corr_frame, textvariable=self.max_correction, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(max_corr_frame, text="設定", command=lambda: self.set_param("MAX_CORR", self.max_correction.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # PIDスケール係数設定
        scale_frame = ttk.Frame(other_params_frame)
        scale_frame.pack(fill=tk.X, pady=2)
        ttk.Label(scale_frame, text="PIDスケール:").pack(side=tk.LEFT, padx=5)
        self.pid_scale = tk.DoubleVar(value=0.01)
        ttk.Entry(scale_frame, textvariable=self.pid_scale, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(scale_frame, text="設定", command=lambda: self.set_param("SCALE", self.pid_scale.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # 最小モーター出力設定
        min_out_frame = ttk.Frame(other_params_frame)
        min_out_frame.pack(fill=tk.X, pady=2)
        ttk.Label(min_out_frame, text="最小出力(µs):").pack(side=tk.LEFT, padx=5)
        self.min_motor_output = tk.IntVar(value=50)
        ttk.Entry(min_out_frame, textvariable=self.min_motor_output, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(min_out_frame, text="設定", command=lambda: self.set_param("MIN_OUT", self.min_motor_output.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # ベース推力設定
        base_thr_frame = ttk.Frame(other_params_frame)
        base_thr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(base_thr_frame, text="ベース推力:").pack(side=tk.LEFT, padx=5)
        self.base_throttle = tk.IntVar(value=1250)
        ttk.Entry(base_thr_frame, textvariable=self.base_throttle, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(base_thr_frame, text="設定", command=lambda: self.set_param("BASE_THR", self.base_throttle.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # D項実装方法選択
        d_method_frame = ttk.LabelFrame(other_params_frame, text="D項実装方法", padding="5")
        d_method_frame.pack(fill=tk.X, pady=5)
        
        d_buttons_frame = ttk.Frame(d_method_frame)
        d_buttons_frame.pack(fill=tk.X)
        
        ttk.Button(
            d_buttons_frame,
            text="D_GYRO",
            command=lambda: self.send_command("D_GYRO"),
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            d_buttons_frame,
            text="D_ERROR", 
            command=lambda: self.send_command("D_ERROR"),
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        # 説明ラベル
        ttk.Label(
            d_method_frame,
            text="D_GYRO: ジャイロ直接使用（高速応答） | D_ERROR: エラー微分使用（スムーズ）",
            font=("Arial", 8)
        ).pack(pady=2)
        
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

    def set_pid_params(self, axis):
        """PIDパラメータ設定"""
        if not self.controller.connected:
            messagebox.showwarning("警告", "デバイスが接続されていません")
            return
        
        if axis == "ROLL":
            kp = self.roll_kp.get()
            ki = self.roll_ki.get()
            kd = self.roll_kd.get()
        elif axis == "PITCH":
            kp = self.pitch_kp.get()
            ki = self.pitch_ki.get()
            kd = self.pitch_kd.get()
        elif axis == "YAW":
            kp = self.yaw_kp.get()
            ki = self.yaw_ki.get()
            kd = self.yaw_kd.get()
        else:
            return
        
        # PIDパラメータを送信
        command = f"PID_{axis} {kp} {ki} {kd}"
        self.controller.send_command(command)
        messagebox.showinfo("設定完了", f"{axis}のPIDパラメータを設定しました\nKp={kp}, Ki={ki}, Kd={kd}")
    
    def set_param(self, param_name, value):
        """その他のパラメータ設定"""
        if not self.controller.connected:
            messagebox.showwarning("警告", "デバイスが接続されていません")
            return
        
        command = f"SET_{param_name} {value}"
        self.controller.send_command(command)
        messagebox.showinfo("設定完了", f"{param_name}を{value}に設定しました")
    
    def send_command(self, command):
        """汎用コマンド送信"""
        if not self.controller.connected:
            messagebox.showwarning("警告", "デバイスが接続されていません")
            return
        
        self.controller.send_command(command)

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
