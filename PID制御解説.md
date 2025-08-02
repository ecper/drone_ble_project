# ドローンPID制御システム解説

## 概要
このドキュメントでは、drone_controller.inoに実装されているPID制御システムについて詳細に解説します。

## 用語集

### 基本用語

| 用語 | 英語 | 意味 | 例・補足 |
|---|---|---|---|
| **PID制御** | PID Control | Proportional-Integral-Derivative（比例・積分・微分）制御の略。自動制御の基本的な手法 | エアコンの温度制御、車のクルーズコントロールなどで使用 |
| **IMU** | Inertial Measurement Unit | 慣性計測装置。加速度センサーとジャイロスコープを組み合わせたセンサー | スマートフォンの画面回転検出にも使用 |
| **PWM** | Pulse Width Modulation | パルス幅変調。デジタル信号でアナログ的な制御を行う技術 | LEDの明るさ調整、モーター速度制御に使用 |
| **ESC** | Electronic Speed Controller | 電子スピードコントローラー。ブラシレスモーターの回転速度を制御する装置 | ドローンの各モーターに1つずつ必要 |
| **Roll** | ロール | 機体の左右の傾き（横転軸周りの回転） | 飛行機が左右に傾く動き |
| **Pitch** | ピッチ | 機体の前後の傾き（横軸周りの回転） | 飛行機が機首を上下する動き |
| **Yaw** | ヨー | 機体の水平面での回転（垂直軸周りの回転） | 飛行機が左右に向きを変える動き |
| **ゲイン** | Gain | 制御の強さを表す係数 | 音量のボリュームのようなもの |
| **エラー** | Error | 目標値と現在値の差 | 設定温度25℃で現在23℃なら、エラーは2℃ |
| **setpoint** | セットポイント | 目標値、設定値 | ドローンの場合は通常0度（水平） |
| **不感帯** | Dead Band | 反応しない範囲 | 小さな振動を無視するための仕組み |
| **積分ワインドアップ** | Integral Windup | 積分項が異常に大きくなる現象 | 長時間エラーが続くと制御が不安定になる |
| **オーバーシュート** | Overshoot | 目標値を超えて行き過ぎること | ブレーキが効きすぎて目標地点を通り過ぎる |
| **定常偏差** | Steady-State Error | 制御が安定した後も残る目標値との差 | 常に少しだけ傾いている状態 |
| **補正値** | Correction Value | 修正するための値 | エラーを解消するための調整量 |
| **µs（マイクロ秒）** | Microseconds | 1/1,000,000秒 | PWM信号の幅を表す単位 |
| **ms（ミリ秒）** | Milliseconds | 1/1,000秒 | 制御周期などの時間単位 |
| **Hz（ヘルツ）** | Hertz | 1秒間の繰り返し回数 | 50Hzは1秒間に50回 |

### センサー関連用語

| 用語 | 意味 | 使用例 |
|---|---|---|
| **加速度センサー** | 加速度（速度の変化）を測定するセンサー | 重力の向きから傾きを計算 |
| **ジャイロスコープ** | 角速度（回転の速さ）を測定するセンサー | どれくらいの速さで回転しているかを検出 |
| **I2C** | Inter-Integrated Circuit。機器間の通信規格 | センサーとマイコンの通信に使用 |

### 数学関連用語

| 用語 | 意味 | 例 |
|---|---|---|
| **atan2** | アークタンジェント2。2つの値から角度を計算する関数 | Y/Xから角度を求める |
| **constrain** | 値を指定範囲内に制限する関数 | constrain(値, 最小, 最大) |
| **abs** | 絶対値（プラスマイナスを取り除いた値） | abs(-5) = 5 |
| **sqrt** | 平方根（ルート） | sqrt(9) = 3 |
| **PI** | 円周率（3.14159...） | 角度変換に使用 |

### 制御理論用語

| 用語 | 意味 | 日常例 |
|---|---|---|
| **比例制御（P）** | エラーの大きさに比例した制御 | ハンドルを切る角度 |
| **積分制御（I）** | エラーの累積に基づく制御 | 長い坂道での速度調整 |
| **微分制御（D）** | エラーの変化速度に基づく制御 | 急ブレーキの強さ |
| **フィードバック制御** | 結果を見ながら調整する制御 | 鏡を見ながら髪を切る |

## PID制御とは何か？

### 日常生活でのPID制御の例

**エアコンの温度制御**を例に説明します：

1. **P（比例）制御**: 
   - 設定温度25℃、現在温度30℃の場合
   - 「5℃も暑い！強く冷やそう」→ 温度差に比例して強く動作

2. **I（積分）制御**:
   - 「30分経っても少し暑いままだ...」
   - 小さなエラーでも長時間続くと、より強く冷やす

3. **D（微分）制御**:
   - 「急に温度が下がり始めた！」
   - 冷やしすぎないようにブレーキをかける

### ドローンでのPID制御

ドローンは常に水平（0度）を保とうとします：
- **右に5度傾いた** → 左側のモーターを強くして水平に戻す
- **傾きが続く** → より強く補正（積分制御）
- **急に傾いた** → 素早く反応しつつ、行き過ぎないよう調整（微分制御）

## 1. PID制御パラメータ定義

```cpp
#define PID_RATE   20            // PID制御周期 (ms)
#define MAX_CORRECTION 150       // 最大PID補正値 (µs)
#define ANGLE_DEADBAND 10.0      // 角度不感帯 (度) ※現在は10度に設定
#define MIN_CORRECTION 30        // 最小補正値 (µs)
#define ANGLE_STOP_MOTOR 5.0     // モーター停止角度 (度) ※現在は5度に設定
```

### パラメータの説明

| パラメータ | 値 | 説明 | 効果 |
|---|---|---|---|
| PID_RATE | 20ms | PID制御周期 | 1秒間に50回（50Hz）の頻度でPID計算を実行。頻度が高いほど滑らかな制御 |
| MAX_CORRECTION | 150µs | PWM補正の上限値 | モーターへの補正信号の最大値。大きすぎると暴走、小さすぎると反応が鈍い |
| ANGLE_DEADBAND | 10.0度 | 角度不感帯 | 10度以下の傾きは「水平」とみなす。風などの外乱を無視する効果 |
| MIN_CORRECTION | 30µs | 最小補正値 | 30µs以下の小さな補正は無効化。モーターの無駄な動作を防ぐ |
| ANGLE_STOP_MOTOR | 5.0度 | モーター停止角度 | 5度以上傾いたらモーター停止（安全機能）※現在の設定値 |

### PWM信号とは？
PWM（パルス幅変調）は、モーターの速度を制御する方法です：
- **1000µs**: モーター停止
- **1500µs**: 中速回転（ホバリング）
- **2000µs**: 最高速回転

例：1450µsの信号 → モーターは約70%の速度で回転

## 2. PID構造体

```cpp
struct PIDController {
  float kp, ki, kd;              // PIDゲイン
  float previous_error;          // 前回のエラー（微分計算用）
  float integral;                // 積分値（累積エラー）
  float setpoint;                // 目標値（通常は0度）
  unsigned long last_time;       // 前回の計算時刻
};
```

### 構造体メンバーの役割

- **kp, ki, kd**: PIDゲイン（制御の強さを決定）
- **previous_error**: 微分項計算のために前回のエラーを保存
- **integral**: 積分項（エラーの累積値）
- **setpoint**: 目標値（ドローンの場合は通常0度の水平状態）
- **last_time**: 時間差分計算用

## 3. PIDコントローラー設定

```cpp
PIDController roll_pid  = {10.0, 0.0, 2.0, 0, 0, 0, 0};   // Roll軸（左右傾き）
PIDController pitch_pid = {10.0, 0.0, 2.0, 0, 0, 0, 0};   // Pitch軸（前後傾き）
PIDController yaw_pid   = {3.0, 0.1, 0.8, 0, 0, 0, 0};    // Yaw軸（回転）
```

### PIDゲインの説明

#### Kp（比例ゲイン）
- **Roll/Pitch**: 10.0
- **Yaw**: 3.0
- **役割**: 現在の角度エラーに対する反応の強さ
- **効果**: 大きいほど強く反応するが、振動しやすくなる
- **現在の問題**: 10.0は非常に高い値で、小さな角度でも大きな補正をかける

#### Ki（積分ゲイン）
- **Roll/Pitch**: 0.0
- **Yaw**: 0.1
- **役割**: 蓄積されたエラーに対する補正
- **効果**: 定常偏差（常に少し傾いている状態）を解消
- **現在の設定**: Roll/Pitchで0.0にしているのは振動防止のため

#### Kd（微分ゲイン）
- **Roll/Pitch**: 2.0
- **Yaw**: 0.8
- **役割**: エラーの変化率に対する反応
- **効果**: 急激な変化を抑制してオーバーシュートを防ぐ

## 4. IMU読み取り関数

```cpp
void readIMU() {
  float ax = imu.readFloatAccelX();
  float ay = imu.readFloatAccelY();
  float az = imu.readFloatAccelZ();
  
  float gx = imu.readFloatGyroX();
  float gy = imu.readFloatGyroY();
  float gz = imu.readFloatGyroZ();
  
  // Roll/Pitch角度計算（加速度から）
  roll_angle = atan2(ay, az) * 180 / PI;
  pitch_angle = atan2(-ax, sqrt(ay*ay + az*az)) * 180 / PI;
  yaw_rate = gz; // Yaw角速度
}
```

### 角度計算の数学的解説

#### 加速度センサーから角度を計算する仕組み

加速度センサーは重力（9.8m/s²）を常に検出しています。機体が傾くと、重力の向きが変わるので、それを利用して角度を計算します。

```
水平状態：           右に傾いた状態：
  ↓重力              ↙重力
  │                ／│
  │               ／ │
──┴──          ──┴──
  az=9.8            ay=4.9, az=8.5
```

#### Roll角（左右の傾き）
```cpp
roll_angle = atan2(ay, az) * 180 / PI;
```
- **atan2(ay, az)**: Y軸とZ軸の加速度の比から角度を計算
- **× 180 / PI**: ラジアン（数学的な角度単位）から度（°）に変換
- 例：右に30度傾くと、roll_angle = 30

#### Pitch角（前後の傾き）
```cpp
pitch_angle = atan2(-ax, sqrt(ay*ay + az*az)) * 180 / PI;
```
- **-ax**: X軸の加速度（マイナスは座標系の関係）
- **sqrt(ay*ay + az*az)**: Y軸とZ軸の合成値（ピタゴラスの定理）
- 例：前に20度傾くと、pitch_angle = 20

#### Yaw角速度（回転速度）
```cpp
yaw_rate = gz;
```
- ジャイロスコープのZ軸値をそのまま使用
- 単位は度/秒（どれくらいの速さで回転しているか）
- 角度ではなく角速度を使う理由：加速度センサーでは水平回転が検出できないため

## 5. PID計算関数

```cpp
float calculatePID(PIDController* pid, float input, float dt) {
  float error = pid->setpoint - input;  // エラー計算
  
  // 積分項
  pid->integral += error * dt;
  pid->integral = constrain(pid->integral, -50, 50);
  
  // 微分項
  float derivative = (error - pid->previous_error) / dt;
  
  // PID出力
  float output = pid->kp * error + pid->ki * pid->integral + pid->kd * derivative;
  
  pid->previous_error = error;
  return constrain(output, -MAX_CORRECTION, MAX_CORRECTION);
}
```

### PID計算の詳細解説

#### 1. エラー計算
```cpp
float error = pid->setpoint - input;
```
- 目標角度（通常0度）と現在角度の差を計算
- 正の値：目標より大きく傾いている
- 負の値：目標より小さく傾いている

#### 2. 積分項（I項）
```cpp
pid->integral += error * dt;
pid->integral = constrain(pid->integral, -50, 50);
```
- **目的**: エラーの時間積分（累積）
- **効果**: 定常偏差の除去
- **制限**: `-50～50`で制限（積分ワインドアップ防止）
- **ワインドアップ**: 積分値が異常に大きくなり制御が不安定になる現象

#### 3. 微分項（D項）
```cpp
float derivative = (error - pid->previous_error) / dt;
```
- **目的**: エラーの変化率を計算
- **効果**: 急激な変化を検出して制動をかける
- **利点**: オーバーシュート（目標を超えて振動）の抑制

#### 4. PID出力計算
```cpp
float output = pid->kp * error + pid->ki * pid->integral + pid->kd * derivative;
```
- **P項**: `Kp * error` - 現在のエラーに比例した補正
- **I項**: `Ki * integral` - 累積エラーに基づく補正
- **D項**: `Kd * derivative` - エラー変化率に基づく補正
- **最終出力**: 3つの項の合計がPWM補正値になる

## 6. PID制御適用関数

```cpp
void applyPIDControl() {
  if (!pid_enabled) return;
  
  unsigned long current_time = millis();
  if (current_time - last_pid_time < PID_RATE) return;
  
  float dt = (current_time - last_pid_time) / 1000.0;
  last_pid_time = current_time;
  
  readIMU();
  
  // 不感帯処理
  if (abs(roll_angle) < ANGLE_DEADBAND) roll_angle = 0;
  if (abs(pitch_angle) < ANGLE_DEADBAND) pitch_angle = 0;
  
  // PID計算
  float roll_correction = calculatePID(&roll_pid, roll_angle, dt);
  float pitch_correction = calculatePID(&pitch_pid, pitch_angle, dt);
  float yaw_correction = calculatePID(&yaw_pid, yaw_rate, dt);
  
  // 最小補正値処理
  if (abs(roll_correction) < MIN_CORRECTION) roll_correction = 0;
  if (abs(pitch_correction) < MIN_CORRECTION) pitch_correction = 0;
  if (abs(yaw_correction) < MIN_CORRECTION) yaw_correction = 0;
  
  // モーターミキシング処理...
}
```

### 制御フローの解説

#### 1. 制御周期管理
- 20ms（50Hz）周期でPID計算を実行
- 高頻度な制御で安定性を確保

#### 2. 不感帯処理
```cpp
if (abs(roll_angle) < ANGLE_DEADBAND) roll_angle = 0;
```
- 5度以下の傾きは0度として扱う
- 微細な振動やノイズの影響を排除

#### 3. 最小補正値処理
```cpp
if (abs(roll_correction) < MIN_CORRECTION) roll_correction = 0;
```
- 30µs以下の補正は無効化
- 小さすぎる補正によるモーターの無駄な動作を防ぐ

## 7. モーターミキシング

```cpp
// Roll制御（左右傾き）
motor_correction[0] = -roll_correction; // 前左
motor_correction[1] = +roll_correction; // 前右
motor_correction[2] = -roll_correction; // 後左
motor_correction[3] = +roll_correction; // 後右

// Pitch制御（前後傾き）
motor_correction[0] += +pitch_correction; // 前左
motor_correction[1] += -pitch_correction; // 前右
motor_correction[2] += -pitch_correction; // 後左
motor_correction[3] += +pitch_correction; // 後右

// Yaw制御（回転）
motor_correction[0] += -yaw_correction; // 前左
motor_correction[1] += +yaw_correction; // 前右
motor_correction[2] += +yaw_correction; // 後左
motor_correction[3] += -yaw_correction; // 後右
```

### モーター配置と制御方向

```
    前（機首）
[0] ⟲ --- ⟳ [1]
 |           |
 |     ✈     |    ⟲: 反時計回り
 |           |    ⟳: 時計回り
[2] ⟳ --- ⟲ [3]
    後（機尾）
```

**重要**: ドローンのプロペラは対角で同じ方向に回転します。これにより機体の回転を相殺しています。

#### Roll制御（左右傾き）の物理的意味

```
右に傾いた状態：        補正動作：
     ＼                  ／
      ＼                ／
機体が右下がり    →   左側(0,2)の推力UP
                      右側(1,3)はそのまま
```

- **右に傾いた場合**: 左側モーター(0,2)の推力を上げて機体を水平に戻す
- **左に傾いた場合**: 右側モーター(1,3)の推力を上げて機体を水平に戻す

#### Pitch制御（前後傾き）の物理的意味

```
前に傾いた状態：        補正動作：
  ↘機首               機首↗
    ＼                  ／
前下がり          →   後側(2,3)の推力UP
                      前側(0,1)の推力DOWN
```

- **前に傾いた場合**: 後側モーター(2,3)の推力を上げ、前側(0,1)を下げる
- **後に傾いた場合**: 前側モーター(0,1)の推力を上げ、後側(2,3)を下げる

#### Yaw制御（回転）の物理的意味

```
時計回り回転を止める：
[0]⟲ ↓ --- ↑ ⟳[1]    反時計回り(0,3)の推力DOWN
              　      時計回り(1,2)の推力UP
[2]⟳ ↑ --- ↓ ⟲[3]    
```

- **時計回りに回転**: 反時計回りプロペラ(0,3)を弱め、時計回り(1,2)を強める
- **反時計回りに回転**: 上記と逆の操作

## 8. 現在の設定の問題点と改善案

### 問題点

1. **Kp=10.0が高すぎる**
   - 現象：小さな角度（例：2度）でも大きな補正（20µs）が入る
   - 結果：機体がガタガタと振動する（ハンチング現象）
   - 例：車のハンドルを切りすぎて蛇行運転になる状態

2. **Ki=0.0（Roll/Pitch）**
   - 現象：微風で少し傾いたままになる
   - 結果：完全に水平に戻らない（定常偏差）
   - 例：坂道で車が少しずつ下がってしまう

3. **不感帯10度（現在の設定）**
   - 現象：10度未満の傾きは完全に無視される
   - 結果：精密な制御ができない
   - 例：10度傾いてもモーターが反応しない

### 改善案

1. **PIDゲインの調整**
   ```cpp
   PIDController roll_pid  = {2.0, 0.1, 0.5, 0, 0, 0, 0};
   PIDController pitch_pid = {2.0, 0.1, 0.5, 0, 0, 0, 0};
   PIDController yaw_pid   = {1.5, 0.05, 0.3, 0, 0, 0, 0};
   ```

2. **不感帯の調整**
   ```cpp
   #define ANGLE_DEADBAND 2.0  // 5.0 → 2.0度に縮小
   ```

3. **段階的な制御の導入**
   - 角度に応じて異なるゲインを適用
   - 小さな角度では穏やかに、大きな角度では強く反応

## 9. 調整手順

### Step 1: Kpの調整
1. Ki, Kdを0にしてKpのみで調整
2. 振動が始まる値を見つける
3. その値の50-70%程度に設定

### Step 2: Kdの追加
1. オーバーシュートを抑制するようにKdを追加
2. 振動が止まる最小値を見つける

### Step 3: Kiの追加
1. 定常偏差を除去するためにKiを少しずつ追加
2. 振動が始まらない範囲で設定

### Step 4: 実機テスト
1. 実際の飛行でファインチューニング
2. 環境や機体特性に合わせて微調整

## 10. デバッグとモニタリング

### 重要な監視項目

1. **角度データ**
   - Roll/Pitch角度が正しく読めているか
   - 機体を傾けた時に値が変化するか

2. **PID出力**
   - 補正値が適切な範囲内か（-150～+150µs）
   - 振動していないか

3. **モーター出力**
   - 4つのモーターのPWM値（1000～2000µs）
   - 差が大きすぎないか

### ログ出力の追加案
```cpp
Serial.print("Roll: "); Serial.print(roll_angle);
Serial.print(" P: "); Serial.print(roll_correction);
Serial.print(" Motors: ");
for(int i=0; i<4; i++) {
  Serial.print(pwm[i]); Serial.print(" ");
}
Serial.println();
```

出力例：
```
Roll: 5.2 P: 52 Motors: 1450 1502 1450 1502
```
これは「右に5.2度傾いているので、右側モーター(1,3)を52µs強くしている」という意味です。

## まとめ

PID制御は、ドローンを安定して飛ばすための「自動バランス機能」です。

- **P制御**：傾きを検出して元に戻す（基本）
- **I制御**：小さな傾きでも時間をかけて修正（精密）  
- **D制御**：急な動きにブレーキをかける（安定）

適切な調整により、風の中でも安定してホバリングできるドローンが完成します。

### 次のステップ

1. まずKpを2.0程度に下げて振動を抑える
2. 不感帯を3度程度に縮小して反応を良くする
3. 実際に飛ばしながら微調整する

安全第一で、少しずつ調整していきましょう！