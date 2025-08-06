#!/usr/bin/env python3
"""
Drone Controller - pygatt version
Uses gatttool as backend
"""

import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import pygatt

# Log settings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BLE settings
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
        """Connect to device"""
        try:
            logger.info("Initializing BLE adapter...")
            self.adapter = pygatt.GATTToolBackend()
            self.adapter.start(reset_on_start=False)

            logger.info(f"Connecting to device {DEVICE_ADDRESS}...")
            self.device = self.adapter.connect(DEVICE_ADDRESS)
            self.connected = True
            logger.info("Connection successful!")

            # Enable notifications
            try:
                self.device.subscribe(STATUS_UUID, callback=self.notification_handler)
                logger.info("Notifications enabled")
            except Exception as e:
                logger.warning(f"Notification enable error: {e}")

            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connected = False
            if self.adapter:
                try:
                    self.adapter.stop()
                except:
                    pass
            return False

    def notification_handler(self, handle, data):
        """BLE notification handler"""
        try:
            status_message = data.decode("utf-8")
            logger.info(f"Status received: {status_message}")
            self.status_queue.put(status_message)
        except Exception as e:
            logger.error(f"Notification processing error: {e}")

    def send_run_command(self):
        """Start/Stop command transmission"""
        if not self.connected or not self.device:
            logger.warning("Cannot transmit command - not connected")
            return False

        try:
            command = "RUN"
            self.send_command(command)
            logger.info(f"Command transmission: {command}")
            return True
        except Exception as e:
            logger.error(f"Transmission error: {e}")
            return False

    def send_stop_command(self):
        """Stop command transmission"""
        if not self.connected or not self.device:
            logger.warning("Cannot transmit command - not connected")
            return False

        try:
            command = "STOP"
            self.send_command(command)
            logger.info(f"Command transmission: {command}")
            return True
        except Exception as e:
            logger.error(f"Transmission error: {e}")
            return False

    def send_command(self, command: str = None):
        """Command transmission"""
        if not self.connected or not self.device:
            logger.warning("Cannot transmit command - not connected")
            return False

        try:
            command = f"{command}"
            self.device.char_write(
                COMMAND_UUID, command.encode(), wait_for_response=False
            )
            logger.info(f"Command transmission: {command}")
            return True

        except Exception as e:
            logger.error(f"Transmission error: {e}")
            return False
    
    def send_parameter(self, param_name, value):
        """Parameter settings command transmission"""
        if not self.connected or not self.device:
            logger.warning("Cannot transmit parameter - not connected")
            return False
        
        try:
            command = f"SET:{param_name}={value}"
            self.device.char_write(COMMAND_UUID, command.encode(), wait_for_response=False)
            logger.info(f"Parameter transmitted: {command}")
            return True
            
        except Exception as e:
            logger.error(f"Parameter transmission error: {e}")
            return False

    def disconnect(self):
        """Disconnect"""
        if self.adapter:
            try:
                self.adapter.stop()
            except:
                pass
        self.connected = False
        logger.info("Disconnected")


class DroneControllerGUI:
    def __init__(self):
        self.controller = DroneController()
        self.root = tk.Tk()
        self.root.title("Drone Controller (pygatt)")
        self.root.geometry("700x1200")

        self.setup_ui()
        self.update_status()

    def setup_ui(self):
        """UI construction"""
        # Header
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)

        ttk.Label(
            header_frame, text="Drone Controller", font=("Arial", 20, "bold")
        ).pack()

        # Connection Status
        self.status_frame = ttk.LabelFrame(self.root, text="Connection Status", padding="10")
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.connection_label = ttk.Label(
            self.status_frame, text="Not Connected", font=("Arial", 12)
        )
        self.connection_label.pack()

        self.status_label = ttk.Label(self.status_frame, text="", font=("Arial", 10))
        self.status_label.pack()

        # Connectbutton
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack()

        self.connect_button = ttk.Button(
            button_frame, text="Connect", command=self.connect_device, width=20
        )
        self.connect_button.pack(side=tk.LEFT, padx=5)

        self.disconnect_button = ttk.Button(
            button_frame,
            text="Disconnect",
            command=self.disconnect_device,
            state=tk.DISABLED,
            width=20,
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=5)

        # Start Buttons
        start_button_frame = ttk.LabelFrame(self.root, text="Start Buttons", padding="10")
        start_button_frame.pack(fill=tk.X, padx=10, pady=10)

        # Start Buttons
        start_button_frame = ttk.Frame(start_button_frame)
        start_button_frame.pack()

        ttk.Button(
            start_button_frame,
            text="Start",
            command=self.start_drone,
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            start_button_frame,
            text="Stop",
            command=self.stop_drone,
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        # ESC Test & Adjustmentframe
        esc_test_frame = ttk.LabelFrame(self.root, text="ESC Test & Adjustment", padding="5")
        esc_test_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # ESC Individual Test Buttons
        test_buttons_frame = ttk.Frame(esc_test_frame)
        test_buttons_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(test_buttons_frame, text="Individual Test:").pack(side=tk.LEFT, padx=5)
        
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
        
        # ESC Offset Adjustment
        offset_frame = ttk.Frame(esc_test_frame)
        offset_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(offset_frame, text="Offset Adjustment:").pack(side=tk.LEFT, padx=5)
        
        # ESC selection and offset Value input
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
        
        ttk.Label(offset_frame, text="value:").pack(side=tk.LEFT, padx=(10,2))
        offset_entry = ttk.Entry(offset_frame, textvariable=self.offset_value, width=6)
        offset_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            offset_frame,
            text="Set",
            command=self.send_offset_command,
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        # Direction Control
        direction_frame = ttk.LabelFrame(self.root, text="Direction Control", padding="10")
        direction_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Main layout (left/right division)
        main_layout_frame = ttk.Frame(direction_frame)
        main_layout_frame.pack(fill=tk.BOTH, expand=True)

        # Left side frame (up/left rotation/right rotation/down)
        left_frame = ttk.LabelFrame(main_layout_frame, text="Up/Down & Rotation", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Upbutton
        ttk.Button(
            left_frame,
            text="Up",
            width=10,
            command=lambda: self.send_direction_command("UP"),
        ).pack(pady=5)

        # Left/right rotation buttons
        rotation_frame = ttk.Frame(left_frame)
        rotation_frame.pack(pady=10)

        ttk.Button(
            rotation_frame,
            text="Left",
            width=10,
            command=lambda: self.send_direction_command("LEFT"),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            rotation_frame,
            text="Right",
            width=10,
            command=lambda: self.send_direction_command("RIGHT"),
        ).pack(side=tk.LEFT, padx=5)

        # Downbutton
        ttk.Button(
            left_frame,
            text="Down",
            width=10,
            command=lambda: self.send_direction_command("DOWN"),
        ).pack(pady=5)

        # Right side frame (forward/Backward)
        right_frame = ttk.LabelFrame(main_layout_frame, text="Forward/Backward Movement", padding="5")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Arrange forward/backward movement buttons vertically
        ttk.Button(
            right_frame,
            text="Forward",
            width=10,
            command=lambda: self.send_direction_command("FWD"),
        ).pack(pady=20)
        ttk.Button(
            right_frame,
            text="Parallel",
            width=10,
            command=lambda: self.send_direction_command("PARALEL"),
        ).pack(pady=20) 
        ttk.Button(
            right_frame,
            text="Backward",
            width=10,
            command=lambda: self.send_direction_command("BACK"),
        ).pack(pady=20)
        

        # PID Parameter Adjustmentframe
        pid_frame = ttk.LabelFrame(self.root, text="PID Parameter Adjustment", padding="10")
        pid_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # PID enable/disable toggle
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
        
        # Roll PID Parameters
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
        ttk.Button(roll_frame, text="Set", command=lambda: self.set_pid_params("ROLL"), width=6).pack(side=tk.LEFT, padx=5)
        
        # Pitch PID Parameters
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
        ttk.Button(pitch_frame, text="Set", command=lambda: self.set_pid_params("PITCH"), width=6).pack(side=tk.LEFT, padx=5)
        
        # Yaw PID Parameters
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
        ttk.Button(yaw_frame, text="Set", command=lambda: self.set_pid_params("YAW"), width=6).pack(side=tk.LEFT, padx=5)
        
        # Simple adjustment buttons
        quick_adjust_frame = ttk.LabelFrame(pid_frame, text="Simple Adjustment", padding="5")
        quick_adjust_frame.pack(fill=tk.X, pady=5)
        
        quick_buttons_frame = ttk.Frame(quick_adjust_frame)
        quick_buttons_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(
            quick_buttons_frame,
            text="Gentle",
            command=lambda: self.send_command("PID_GENTLE"),
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            quick_buttons_frame,
            text="Standard",
            command=lambda: self.send_command("PID_NORMAL"),
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            quick_buttons_frame,
            text="Aggressive",
            command=lambda: self.send_command("PID_AGGRESSIVE"),
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        # Simple switching of D-term implementation method
        d_quick_frame = ttk.Frame(pid_frame)
        d_quick_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(d_quick_frame, text="D-term Method:").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            d_quick_frame,
            text="Gyro",
            command=lambda: self.send_command("D_GYRO"),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            d_quick_frame,
            text="Error Derivative",
            command=lambda: self.send_command("D_ERROR"),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        # Other Parameters
        other_params_frame = ttk.LabelFrame(pid_frame, text="Other Parameters", padding="5")
        other_params_frame.pack(fill=tk.X, pady=5)
        
        # deadbandSet
        deadband_frame = ttk.Frame(other_params_frame)
        deadband_frame.pack(fill=tk.X, pady=2)
        ttk.Label(deadband_frame, text="Angle Deadband (degrees):").pack(side=tk.LEFT, padx=5)
        self.angle_deadband = tk.DoubleVar(value=0.1)
        ttk.Entry(deadband_frame, textvariable=self.angle_deadband, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(deadband_frame, text="Set", command=lambda: self.set_param("DEADBAND", self.angle_deadband.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # Min correction value settings
        min_corr_frame = ttk.Frame(other_params_frame)
        min_corr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(min_corr_frame, text="Min Correction Value (µs):").pack(side=tk.LEFT, padx=5)
        self.min_correction = tk.IntVar(value=30)
        ttk.Entry(min_corr_frame, textvariable=self.min_correction, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(min_corr_frame, text="Set", command=lambda: self.set_param("MIN_CORR", self.min_correction.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # Max correction value settings
        max_corr_frame = ttk.Frame(other_params_frame)
        max_corr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_corr_frame, text="Max Correction Value (µs):").pack(side=tk.LEFT, padx=5)
        self.max_correction = tk.IntVar(value=100)
        ttk.Entry(max_corr_frame, textvariable=self.max_correction, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(max_corr_frame, text="Set", command=lambda: self.set_param("MAX_CORR", self.max_correction.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # PID scale factor settings
        scale_frame = ttk.Frame(other_params_frame)
        scale_frame.pack(fill=tk.X, pady=2)
        ttk.Label(scale_frame, text="PID Scale:").pack(side=tk.LEFT, padx=5)
        self.pid_scale = tk.DoubleVar(value=0.01)
        ttk.Entry(scale_frame, textvariable=self.pid_scale, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(scale_frame, text="Set", command=lambda: self.set_param("SCALE", self.pid_scale.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # Min motor output settings
        min_out_frame = ttk.Frame(other_params_frame)
        min_out_frame.pack(fill=tk.X, pady=2)
        ttk.Label(min_out_frame, text="Min Output (µs):").pack(side=tk.LEFT, padx=5)
        self.min_motor_output = tk.IntVar(value=50)
        ttk.Entry(min_out_frame, textvariable=self.min_motor_output, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(min_out_frame, text="Set", command=lambda: self.set_param("MIN_OUT", self.min_motor_output.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # Base Throttle Settings
        base_thr_frame = ttk.Frame(other_params_frame)
        base_thr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(base_thr_frame, text="Base Throttle:").pack(side=tk.LEFT, padx=5)
        self.base_throttle = tk.IntVar(value=1250)
        ttk.Entry(base_thr_frame, textvariable=self.base_throttle, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(base_thr_frame, text="Set", command=lambda: self.set_param("BASE_THR", self.base_throttle.get()), width=6).pack(side=tk.LEFT, padx=5)
        
        # D-term implementation method selection
        d_method_frame = ttk.LabelFrame(other_params_frame, text="D-term Implementation Method", padding="5")
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
        
        # Explanation label
        ttk.Label(
            d_method_frame,
            text="D_GYRO: Direct gyro use (fast response) | D_ERROR: Error derivative use (smooth)",
            font=("Arial", 8)
        ).pack(pady=2)
        
        # urgentStop
        ttk.Button(
            self.root,
            text="Emergency Stop",
            command=self.emergency_stop,
            style="Emergency.TButton",
        ).pack(pady=20)

        # styleSet
        style = ttk.Style()
        style.configure(
            "Emergency.TButton", foreground="red", font=("Arial", 16, "bold")
        )

    def connect_device(self):
        """Connect to device"""
        self.connect_button.config(state=tk.DISABLED, text="Connecting...")

        # Connect in separate thread
        def _connect():
            success = self.controller.connect_to_device()
            self.root.after(0, self.on_connection_result, success)

        threading.Thread(target=_connect, daemon=True).start()

    def disconnect_device(self):
        """Disconnect from device"""
        self.controller.disconnect()
        self.on_disconnected()

    def start_drone(self):
        """Start drone"""
        self.controller.send_run_command()

    def stop_drone(self):
        """Stop drone"""
        self.controller.send_stop_command()


    def send_direction_command(self, command: str = None):
        """Direction command transmission"""
        if not self.controller.connected:
            messagebox.showwarning("Warning", "Device is not connected")
            return

        self.controller.send_command(command)

    def send_test_command(self, esc_num):
        """ESC individual test command transmission"""
        if not self.controller.connected:
            messagebox.showwarning("Warning", "Device is not connected")
            return
        
        command = f"TEST{esc_num}"
        self.controller.send_command(command)
        messagebox.showinfo("Test", f"ESC{esc_num} individual test started")

    def send_offset_command(self):
        """ESC offset adjustment command transmission"""
        if not self.controller.connected:
            messagebox.showwarning("Warning", "Device is not connected")
            return
        
        esc_num = self.selected_esc.get()
        offset_val = self.offset_value.get()
        
        # Range check
        if offset_val < -200 or offset_val > 200:
            messagebox.showerror("Error", "Please input offset value in range -200 to 200")
            return
        
        command = f"OFFSET{esc_num} {offset_val}"
        self.controller.send_command(command)
        messagebox.showinfo("Settings Complete", f"ESC{esc_num} offset set to {offset_val}")

    def set_pid_params(self, axis):
        """PID parameter settings"""
        if not self.controller.connected:
            messagebox.showwarning("Warning", "Device is not connected")
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
        
        # Transmit PID parameters
        command = f"PID_{axis} {kp} {ki} {kd}"
        self.controller.send_command(command)
        messagebox.showinfo("Settings Complete", f"{axis} PID parameters set\nKp={kp}, Ki={ki}, Kd={kd}")
    
    def set_param(self, param_name, value):
        """Other parameter settings"""
        if not self.controller.connected:
            messagebox.showwarning("Warning", "Device is not connected")
            return
        
        command = f"SET_{param_name} {value}"
        self.controller.send_command(command)
        messagebox.showinfo("Settings Complete", f"{param_name} set to {value}")
    
    def send_command(self, command):
        """Generic command transmission"""
        if not self.controller.connected:
            messagebox.showwarning("Warning", "Device is not connected")
            return
        
        self.controller.send_command(command)

    def emergency_stop(self):
        """Emergency stop"""
        if self.controller.connected:
            self.controller.send_stop_command()
            messagebox.showinfo("Emergency Stop", "Motors stopped")

    def on_connection_result(self, success):
        """Connection result processing"""
        if success:
            self.connection_label.config(text="Connected", foreground="green")
            self.connect_button.config(state=tk.DISABLED, text="Connect")
            self.disconnect_button.config(state=tk.NORMAL)
        else:
            self.connection_label.config(text="Connection Failed", foreground="red")
            self.connect_button.config(state=tk.NORMAL, text="Connect")
            messagebox.showerror("Error", "Failed to connect to device")

    def on_disconnected(self):
        """Disconnection processing"""
        self.connection_label.config(text="Not Connected", foreground="black")
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)

    def update_status(self):
        """Status update"""
        try:
            while not self.controller.status_queue.empty():
                status = self.controller.status_queue.get_nowait()
                self.status_label.config(text=f"status: {status}")
        except queue.Empty:
            pass

        self.root.after(100, self.update_status)

    def run(self):
        """Application execution"""
        try:
            self.root.mainloop()
        finally:
            self.controller.disconnect()


def main():
    """Main function"""
    # Check if pygatt is installed
    try:
        import pygatt
    except ImportError:
        print("pygatt is not installed.")
        print("Please install with the following command:")
        print("  pip install pygatt")
        return

    app = DroneControllerGUI()
    app.run()


if __name__ == "__main__":
    main()
