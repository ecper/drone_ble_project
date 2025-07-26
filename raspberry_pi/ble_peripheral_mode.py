#!/usr/bin/env python3
"""
BLEペリフェラルモードでペアリング不要の設定を行うスクリプト
"""
import subprocess
import time
import sys

def execute_command(cmd):
    """コマンドを実行して結果を表示"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to execute: {cmd}")
        print(f"Error: {e}")
        return False

def setup_ble_peripheral():
    """BLEペリフェラルとして設定"""
    
    print("=== BLEペリフェラルモード設定 ===")
    
    # 1. 既存のペアリング情報をクリア
    print("\n1. 既存のペアリング情報をクリア...")
    execute_command("sudo systemctl stop bluetooth")
    execute_command("sudo rm -rf /var/lib/bluetooth/*")
    execute_command("sudo systemctl start bluetooth")
    time.sleep(2)
    
    # 2. hciconfigで設定
    print("\n2. HCIデバイス設定...")
    execute_command("sudo hciconfig hci0 up")
    execute_command("sudo hciconfig hci0 noscan")  # スキャンを無効化
    execute_command("sudo hciconfig hci0 pscan")   # ページスキャンのみ有効
    execute_command("sudo hciconfig hci0 sspmode 1")  # Simple Secure Pairing有効
    execute_command("sudo hciconfig hci0 noauth")  # 認証不要
    execute_command("sudo hciconfig hci0 noencrypt")  # 暗号化不要
    
    # 3. bluetoothctlで設定
    print("\n3. bluetoothctl設定...")
    commands = """
power on
agent off
pairable off
discoverable on
quit
"""
    
    process = subprocess.Popen(['sudo', 'bluetoothctl'], 
                             stdin=subprocess.PIPE, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE,
                             text=True)
    
    stdout, stderr = process.communicate(input=commands)
    if stdout:
        print(f"bluetoothctl output: {stdout}")
    
    # 4. 設定確認
    print("\n4. 現在の設定確認...")
    execute_command("sudo hciconfig hci0 -a")
    
    print("\n=== 設定完了 ===")
    print("ペアリング不要のBLEペリフェラルとして設定されました。")
    print("drone_ble_server.pyを起動してください。")

if __name__ == "__main__":
    setup_ble_peripheral()