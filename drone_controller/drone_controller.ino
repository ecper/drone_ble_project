/*
* Quad‑ESC Controller  v7 with PID Control
*  RUN  : 現在値 → HOVER_THR へ ふわっと加速（ランプアップ）
*  STOP : 1回目 LAND_THR で降下保持, 2回目 ESC_MIN で完全停止
*  方向/UP/DOWN/PARALLEL : 即時に推力変更・保持
*  PID制御による姿勢安定化
*/


#include <Wire.h>
#include <Servo.h>
#include <LSM6DS3.h>
#include <MadgwickAHRS.h>


#define SLAVE_ADDR 0x08
#define ESC_MIN    1000
#define ESC_MAX    2000
#define HOVER_THR  1250          // ホバリング推力
#define LAND_THR   1250          // 降下推力
#define DELTA_XY   10
#define DELTA_Z    10
#define RAMP_STEP  10            // 1 ステップあたりの増分 (µs)
#define RAMP_DELAY 15            // ステップ間ウエイト (ms)

// PID制御パラメータ
#define PID_RATE   20            // PID制御周期 (ms)

// 動的に調整可能なパラメータ（参考コードベース）
float angle_deadband = 0.5;      // 角度不感帯 (度) - 1度以下は無視
int16_t min_correction = 5;      // 最小補正値 (µs) - 微細な調整も有効
int16_t max_correction = 100;    // 最大PID補正値 (µs) - 参考コードに合わせて増加

// PIDスケーリング係数（参考コードから）
float pid_scale_factor = 0.5;   // PID出力のスケーリング（1.0でそのまま使用）
int16_t min_motor_output = 50;   // モーター最小出力保証（ESC_MIN + この値）
float i_limit = 25.0;           // 積分項制限値

// PID構造体
struct PIDController {
  float kp, ki, kd;
  float previous_error;
  float integral;
  float setpoint;
  unsigned long last_time;
};

// センサーとESC
LSM6DS3 imu(I2C_MODE, 0x6A);
Servo esc[4];
const uint8_t escPin[4] = {0, 1, 2, 3};

// Madgwickフィルター
Madgwick filter;

// PIDコントローラー（参考コードベースの値）
PIDController roll_pid  = {3.0, 0.01, 0.5, 0, 0, 0, 0};   // 参考コードの標準値
PIDController pitch_pid = {3.0, 0.01, 0.5, 0, 0, 0, 0};   // 参考コードの標準値
PIDController yaw_pid   = {3.0, 0.01, 0.5, 0, 0, 0, 0};   // Yawは少し控えめ

// 姿勢データ（改良版）
float roll_angle = 0, pitch_angle = 0, yaw_rate = 0;
float roll_gyro = 0, pitch_gyro = 0, yaw_gyro = 0;  // ジャイロ値追加
bool pid_enabled = false;
unsigned long last_pid_time = 0;

// ベース推力管理
uint16_t base_throttle = HOVER_THR;  // ベース推力

// ESC個別調整用オフセット
int16_t esc_offset[4] = {45, -5, -5, -30};  // 各ESCの補正値(FR, BL, BR, FL)


char buf[40];  byte idx = 0;
bool landing = false;            // STOP1 → true
uint16_t pwm[4] = {ESC_MIN, ESC_MIN, ESC_MIN, ESC_MIN}; // 常に現在値を保持



/* ---------- PIDリセット ---------- */
void resetPID() {
  // 目標角度を0に
  roll_pid.setpoint = 0.0;
  pitch_pid.setpoint = 0.0;
  yaw_pid.setpoint = 0.0;
  
  // 積分項をリセット
  roll_pid.integral = 0.0;
  pitch_pid.integral = 0.0;
  yaw_pid.integral = 0.0;
  
  // 前回のエラーもリセット
  roll_pid.previous_error = 0.0;
  pitch_pid.previous_error = 0.0;
  yaw_pid.previous_error = 0.0;
}

/* ---------- IMU読み取り（Madgwickフィルター版） ---------- */
void readIMU() {
  float ax = imu.readFloatAccelX();
  float ay = imu.readFloatAccelY();
  float az = imu.readFloatAccelZ();
  
  float gx = imu.readFloatGyroX();
  float gy = imu.readFloatGyroY();
  float gz = imu.readFloatGyroZ();
  
  // 元の角度計算方法（Madgwickが動かない場合の比較用）
  float roll_from_accel = atan2(ay, az) * 180 / PI;
  float pitch_from_accel = atan2(-ax, sqrt(ay*ay + az*az)) * 180 / PI;
  
  // Madgwickフィルターで姿勢を更新（磁気センサーなしの6軸）
  // 磁気センサーのデータには0を渡す
  filter.update(gx, gy, gz, ax, ay, az, 0, 0, 0);
  
  // フィルターから角度を取得
  // 一時的に加速度ベースの角度を使用（Madgwickが動作しない場合）
  roll_angle = roll_from_accel;  // filter.getRoll();
  pitch_angle = pitch_from_accel; // filter.getPitch();
  float yaw_angle = filter.getYaw();  // Yaw角度（使用する場合）
  
  // デバッグ出力：加速度計算とMadgwick出力の比較
  static unsigned long lastDebugTime = 0;
  if (millis() - lastDebugTime > 500) {  // 500ms毎に出力
    lastDebugTime = millis();
    Serial.print("Accel angles - R: "); Serial.print(roll_from_accel);
    Serial.print(" P: "); Serial.print(pitch_from_accel);
    Serial.print(" | Madgwick - R: "); Serial.print(roll_angle);
    Serial.print(" P: "); Serial.println(pitch_angle);
  }
  
  // ジャイロ値も保存（PID微分項用）
  roll_gyro = gx;   // Roll角速度
  pitch_gyro = gy;  // Pitch角速度  
  yaw_gyro = gz;    // Yaw角速度（Yaw制御に使用）
  yaw_rate = gz;    // 互換性のため
}

/* ---------- PID計算（改良版） ---------- */
float calculatePID(PIDController* pid, float input, float gyro_rate, float dt) {
  float error = pid->setpoint - input;
  
  // 不感帯処理
  if (abs(error) < angle_deadband) {
    error = 0.0;
  }
  
  // 積分項（参考コードの手法）
  pid->integral += error * dt;
  pid->integral = constrain(pid->integral, -i_limit, i_limit); // 積分ワインドアップ防止
  
  // 微分項（参考コードの手法：ジャイロ値を直接使用）
  float derivative = gyro_rate; // ジャイロ値をそのまま使用（度/秒）
  
  // PID出力計算
  float output = pid->kp * error + pid->ki * pid->integral + pid->kd * derivative;
  
  // スケーリング（参考コードから）
  output = output * pid_scale_factor;
  
  pid->previous_error = error;
  return constrain(output, -max_correction, max_correction);
}

/* ---------- PID制御適用（改良版） ---------- */
void applyPIDControl() {
  if (!pid_enabled) return;
  
  unsigned long current_time = millis();
  if (current_time - last_pid_time < PID_RATE) return;
  
  float dt = (current_time - last_pid_time) / 1000.0;
  last_pid_time = current_time;
  
  readIMU();
  
  // デバッグ出力（500ms毎）
  static unsigned long lastPIDDebug = 0;
  if (millis() - lastPIDDebug > 500) {
    lastPIDDebug = millis();
    Serial.print("PID Debug - Roll: "); Serial.print(roll_angle);
    Serial.print(" Pitch: "); Serial.print(pitch_angle);
    Serial.print(" Enabled: "); Serial.println(pid_enabled);
  }
  
  // PID計算（ジャイロ値を微分項として使用）
  float roll_correction = calculatePID(&roll_pid, roll_angle, roll_gyro, dt);
  float pitch_correction = calculatePID(&pitch_pid, pitch_angle, pitch_gyro, dt);
  float yaw_correction = calculatePID(&yaw_pid, yaw_rate, yaw_gyro, dt);
  
  // モーター配置：
  // 0: FR (前右), 1: BL (後左), 2: BR (後右), 3: FL (前左)
  
  // ベース推力からの補正量計算（参考コードの手法）
  float motor_output[4];
  
  // Roll制御（右に傾いたら右側のモーターを強く）
  motor_output[0] = base_throttle - roll_correction; // FR
  motor_output[1] = base_throttle + roll_correction; // BL  
  motor_output[2] = base_throttle - roll_correction; // BR
  motor_output[3] = base_throttle + roll_correction; // FL
  
  // Pitch制御（前に傾いたら後ろ側のモーターを強く）
  motor_output[0] += pitch_correction; // FR
  motor_output[1] -= pitch_correction; // BL
  motor_output[2] -= pitch_correction; // BR
  motor_output[3] += pitch_correction; // FL
  
  // Yaw制御（時計回りを止めるには反時計回りモーターを強く）
  motor_output[0] += yaw_correction; // FR (時計回り)
  motor_output[1] += yaw_correction; // BL (反時計回り)
  motor_output[2] -= yaw_correction; // BR (時計回り)
  motor_output[3] -= yaw_correction; // FL (反時計回り)
  
  // 最小モーター出力保証と範囲制限
  for (byte i = 0; i < 4; i++) {
    // 最小出力保証
    if (motor_output[i] < ESC_MIN + min_motor_output) {
      motor_output[i] = ESC_MIN + min_motor_output;
    }
    // 最大値制限
    pwm[i] = constrain(motor_output[i], ESC_MIN, ESC_MAX);
  }
  
  // デバッグ出力（500ms毎）
  static unsigned long lastCorrectionDebug = 0;
  if (millis() - lastCorrectionDebug > 500) {
    lastCorrectionDebug = millis();
    Serial.print("Corrections - R: "); Serial.print(roll_correction);
    Serial.print(" P: "); Serial.print(pitch_correction);
    Serial.print(" Y: "); Serial.println(yaw_correction);
  }
  
  writeNow();
}

/* ---------- 低レベル ---------- */
void writeNow() {
 // デバッグ出力制御（PID有効時のみ）
 static unsigned long lastWriteDebug = 0;
 bool shouldPrint = pid_enabled && (millis() - lastWriteDebug > 1000);
 if (shouldPrint) lastWriteDebug = millis();
 
 for (byte i = 0; i < 4; i++) {
   uint16_t pw = constrain(pwm[i] + esc_offset[i], ESC_MIN, ESC_MAX);
   esc[i].writeMicroseconds(pw);
   pwm[i] = pw - esc_offset[i];  // 元の値を保持
   
   if (shouldPrint) {
     Serial.print("ESC"); Serial.print(i);
     Serial.print("="); Serial.print(pw);
     if (esc_offset[i] != 0) {
       Serial.print("("); Serial.print(pwm[i]); Serial.print("+"); Serial.print(esc_offset[i]); Serial.print(")");
     }
     Serial.print(" ");
   }
 }
 if (shouldPrint) Serial.println();
}


void stopAll() {
 for (byte i = 0; i < 4; i++) pwm[i] = ESC_MIN;
 writeNow();
}


/* ---------- ランプアップ ---------- */
void rampTo(uint16_t tgt) {
 bool done = false;
 while (!done) {
   done = true;
   for (byte i = 0; i < 4; i++) {
     if (pwm[i] < tgt) {
       pwm[i] = (pwm[i] + RAMP_STEP > tgt) ? tgt : pwm[i] + RAMP_STEP;
       done = false;
     } else if (pwm[i] > tgt) {
       pwm[i] = (pwm[i] < tgt + RAMP_STEP) ? tgt : pwm[i] - RAMP_STEP;
       done = false;
     }
   }
   writeNow();
   delay(RAMP_DELAY);
 }
}


/* ---------- コマンド適用 ---------- */
void applyCmd(const char *cmd) {


 /* RUN ---------------------------------------------------------------- */
 if (!strcmp(cmd, "RUN")) {
   base_throttle = HOVER_THR;   // ベース推力を設定
   rampTo(HOVER_THR);          // 現在値→1450 µs へ滑らかに変化
   landing = false;
   pid_enabled = true;         // PID制御開始
   last_pid_time = millis();
   resetPID();                 // PIDパラメータを初期化
   return;
 }


 /* STOP --------------------------------------------------------------- */
 if (!strcmp(cmd, "STOP")) {
   pid_enabled = false;        // まずPID制御を停止
   // 目標角度をリセット
   roll_pid.setpoint = 0.0;
   pitch_pid.setpoint = 0.0;
   yaw_pid.setpoint = 0.0;
   if (!landing) {             // 1 回目：降下推力で保持
     rampTo(LAND_THR);
     landing = true;
   } else {                    // 2 回目：完全停止
     stopAll();
     landing = false;
   }
   return;
 }

/* 緊急停止 --------------------------------------------------------- */
 else if (!strcmp(cmd,"EMERGENCY") || !strcmp(cmd,"ESTOP")) {
   pid_enabled = false;
   stopAll();
   landing = false;
   Serial.println("EMERGENCY STOP!");
   return;
 }



 /* 方向 / 上下 -------------------------------------------------------- */
 if (!strcmp(cmd,"FWD"))  {
   if (pid_enabled) {
     // PID制御時：目標角度を設定（前進は機首を下げる）
     pitch_pid.setpoint = -5.0;  // -5度
   } else {
     // 通常制御時：PWM値を直接調整
     pwm[0]-=DELTA_XY; pwm[1]-=DELTA_XY; pwm[2]+=DELTA_XY; pwm[3]+=DELTA_XY;
   }
 }
 else if (!strcmp(cmd,"BACK")) {
   if (pid_enabled) {
     // PID制御時：目標角度を設定（後退は機首を上げる）
     pitch_pid.setpoint = 5.0;   // +5度
   } else {
     // 通常制御時：PWM値を直接調整
     pwm[0]+=DELTA_XY; pwm[1]+=DELTA_XY; pwm[2]-=DELTA_XY; pwm[3]-=DELTA_XY;
   }
 }
 else if (!strcmp(cmd,"LEFT")) {
   if (pid_enabled) {
     // PID制御時：目標角度を設定（左移動は右に傾ける）
     roll_pid.setpoint = 5.0;    // +5度
   } else {
     // 通常制御時：PWM値を直接調整
     pwm[0]-=DELTA_XY; pwm[1]+=DELTA_XY; pwm[2]-=DELTA_XY; pwm[3]+=DELTA_XY;
   }
 }
 else if (!strcmp(cmd,"RIGHT")){
   if (pid_enabled) {
     // PID制御時：目標角度を設定（右移動は左に傾ける）
     roll_pid.setpoint = -5.0;   // -5度
   } else {
     // 通常制御時：PWM値を直接調整
     pwm[0]+=DELTA_XY; pwm[1]-=DELTA_XY; pwm[2]+=DELTA_XY; pwm[3]-=DELTA_XY;
   }
 }
 else if (!strcmp(cmd,"UP"))   {
   if (pid_enabled) {
     // PID制御時：ベース推力を増加
     base_throttle = constrain(base_throttle + DELTA_Z, ESC_MIN + min_motor_output, ESC_MAX - max_correction);
   } else {
     // 通常制御時：全体の推力を増加
     for(byte i=0;i<4;i++) pwm[i]+=DELTA_Z;
   }
 }
 else if (!strcmp(cmd,"DOWN")) {
   if (pid_enabled) {
     // PID制御時：ベース推力を減少
     base_throttle = constrain(base_throttle - DELTA_Z, ESC_MIN + min_motor_output, ESC_MAX - max_correction);
   } else {
     // 通常制御時：全体の推力を減少
     for(byte i=0;i<4;i++) pwm[i]-=DELTA_Z;
   }
 }
 else if (!strcmp(cmd,"PALALEL")){
   if (pid_enabled) {
     // PID制御時：目標角度を水平（0度）に戻す
     roll_pid.setpoint = 0.0;
     pitch_pid.setpoint = 0.0;
     yaw_pid.setpoint = 0.0;
   } else {
     // 通常制御時：全モーターをホバリング推力に
     for(byte i=0;i<4;i++) pwm[i]=HOVER_THR;
   }
 }
 else if (!strcmp(cmd,"PID_ON")) {
   pid_enabled = true; 
   last_pid_time = millis();
   resetPID();  // PIDパラメータを初期化
 }
 else if (!strcmp(cmd,"PID_OFF")) {
   pid_enabled = false;
   // 目標角度のみリセット（積分項は保持）
   roll_pid.setpoint = 0.0;
   pitch_pid.setpoint = 0.0;
   yaw_pid.setpoint = 0.0;
 }
 
 /* ESC個別テスト ---------------------------------------------------- */
else if (!strcmp(cmd,"TEST0")) {
   pid_enabled = false;  // PID制御を無効化
   stopAll(); 
   pwm[0]=HOVER_THR;  // ESC0のみホバリング推力
   writeNow();         // 変更を適用
   return;
 }
 else if (!strcmp(cmd,"TEST1")) {
   pid_enabled = false;
   stopAll(); 
   pwm[1]=HOVER_THR;  // ESC1のみホバリング推力
   writeNow();         // 変更を適用
   return;
 }
 else if (!strcmp(cmd,"TEST2")) {
   pid_enabled = false;
   stopAll(); 
   pwm[2]=HOVER_THR;  // ESC2のみホバリング推力
   writeNow();         // 変更を適用
   return;
 }
 else if (!strcmp(cmd,"TEST3")) {
   pid_enabled = false;
   stopAll(); 
   pwm[3]=HOVER_THR;  // ESC3のみホバリング推力
   writeNow();         // 変更を適用
   return;
 }

 /* ESCオフセット調整 ----------------------------------------------- */
 else if (strncmp(cmd, "OFFSET", 6) == 0) {
   int esc_num, offset_val;
   if (sscanf(cmd, "OFFSET%d %d", &esc_num, &offset_val) == 2) {
     if (esc_num >= 0 && esc_num <= 3) {
       esc_offset[esc_num] = constrain(offset_val, -200, 200);
       Serial.print("ESC"); Serial.print(esc_num); 
       Serial.print(" offset = "); Serial.println(esc_offset[esc_num]);
     }
   }
   return;
 }
 
 /* PIDパラメータ設定 ------------------------------------------------ */
 else if (strncmp(cmd, "PID_ROLL", 8) == 0) {
   float kp, ki, kd;
   if (sscanf(cmd, "PID_ROLL %f %f %f", &kp, &ki, &kd) == 3) {
     roll_pid.kp = kp;
     roll_pid.ki = ki;
     roll_pid.kd = kd;
     Serial.print("Roll PID set: Kp="); Serial.print(kp);
     Serial.print(" Ki="); Serial.print(ki);
     Serial.print(" Kd="); Serial.println(kd);
   }
   return;
 }
 else if (strncmp(cmd, "PID_PITCH", 9) == 0) {
   float kp, ki, kd;
   if (sscanf(cmd, "PID_PITCH %f %f %f", &kp, &ki, &kd) == 3) {
     pitch_pid.kp = kp;
     pitch_pid.ki = ki;
     pitch_pid.kd = kd;
     Serial.print("Pitch PID set: Kp="); Serial.print(kp);
     Serial.print(" Ki="); Serial.print(ki);
     Serial.print(" Kd="); Serial.println(kd);
   }
   return;
 }
 else if (strncmp(cmd, "PID_YAW", 7) == 0) {
   float kp, ki, kd;
   if (sscanf(cmd, "PID_YAW %f %f %f", &kp, &ki, &kd) == 3) {
     yaw_pid.kp = kp;
     yaw_pid.ki = ki;
     yaw_pid.kd = kd;
     Serial.print("Yaw PID set: Kp="); Serial.print(kp);
     Serial.print(" Ki="); Serial.print(ki);
     Serial.print(" Kd="); Serial.println(kd);
   }
   return;
 }
 
 /* その他のパラメータ設定 ------------------------------------------- */
 else if (strncmp(cmd, "SET_DEADBAND", 12) == 0) {
   float value;
   if (sscanf(cmd, "SET_DEADBAND %f", &value) == 1) {
     angle_deadband = constrain(value, 0.0, 45.0);  // 0～45度の範囲
     Serial.print("DEADBAND set to: "); Serial.println(angle_deadband);
   }
   return;
 }
 else if (strncmp(cmd, "SET_MIN_CORR", 12) == 0) {
   int value;
   if (sscanf(cmd, "SET_MIN_CORR %d", &value) == 1) {
     min_correction = constrain(value, 0, 100);  // 0～100µsの範囲
     Serial.print("MIN_CORRECTION set to: "); Serial.println(min_correction);
   }
   return;
 }
 else if (strncmp(cmd, "SET_MAX_CORR", 12) == 0) {
   int value;
   if (sscanf(cmd, "SET_MAX_CORR %d", &value) == 1) {
     max_correction = constrain(value, 5, 200);  // 5～200µsの範囲（安全のため上限下げ）
     Serial.print("MAX_CORRECTION set to: "); Serial.println(max_correction);
   }
   return;
 }
 
 /* 簡単調整コマンド ------------------------------------------------- */
 else if (!strcmp(cmd, "PID_GENTLE")) {
   // より穏やかなPID設定（参考コードベース）
   roll_pid.kp = 3.0; roll_pid.ki = 0.0; roll_pid.kd = 0.5;
   pitch_pid.kp = 3.0; pitch_pid.ki = 0.0; pitch_pid.kd = 0.5;
   yaw_pid.kp = 2.0; yaw_pid.ki = 0.0; yaw_pid.kd = 0.3;
   pid_scale_factor = 0.5;  // 穏やかなスケール
   Serial.println("PID set to GENTLE mode");
   return;
 }
 else if (!strcmp(cmd, "PID_NORMAL")) {
   // 標準的なPID設定（参考コードベース）
   roll_pid.kp = 6.0; roll_pid.ki = 0.0; roll_pid.kd = 0.8;
   pitch_pid.kp = 6.0; pitch_pid.ki = 0.0; pitch_pid.kd = 0.8;
   yaw_pid.kp = 4.0; yaw_pid.ki = 0.0; yaw_pid.kd = 0.5;
   pid_scale_factor = 1.0;   // 標準スケール（そのまま）
   Serial.println("PID set to NORMAL mode");
   return;
 }
 else if (!strcmp(cmd, "PID_AGGRESSIVE")) {
   // より積極的なPID設定（上級者向け）
   roll_pid.kp = 10.0; roll_pid.ki = 0.1; roll_pid.kd = 1.2;
   pitch_pid.kp = 10.0; pitch_pid.ki = 0.1; pitch_pid.kd = 1.2;
   yaw_pid.kp = 6.0; yaw_pid.ki = 0.05; yaw_pid.kd = 0.8;
   pid_scale_factor = 1.5;  // より大きなスケール
   Serial.println("PID set to AGGRESSIVE mode");
   return;
 }
 
 /* 詳細パラメータ調整 ------------------------------------------- */
 else if (strncmp(cmd, "SET_SCALE", 9) == 0) {
   float value;
   if (sscanf(cmd, "SET_SCALE %f", &value) == 1) {
     pid_scale_factor = constrain(value, 0.001, 0.1);
     Serial.print("PID scale factor set to: "); Serial.println(pid_scale_factor);
   }
   return;
 }
 else if (strncmp(cmd, "SET_MIN_OUT", 11) == 0) {
   int value;
   if (sscanf(cmd, "SET_MIN_OUT %d", &value) == 1) {
     min_motor_output = constrain(value, 10, 200);
     Serial.print("Min motor output set to: "); Serial.println(min_motor_output);
   }
   return;
 }
 else if (strncmp(cmd, "SET_BASE_THR", 12) == 0) {
   int value;
   if (sscanf(cmd, "SET_BASE_THR %d", &value) == 1) {
     base_throttle = constrain(value, ESC_MIN + min_motor_output, ESC_MAX - max_correction);
     Serial.print("Base throttle set to: "); Serial.println(base_throttle);
   }
   return;
 }
 
 /* 設定表示 --------------------------------------------------------- */
 else if (!strcmp(cmd,"STATUS")) {
   Serial.println("=== ESC Status ===");
   for (byte i = 0; i < 4; i++) {
     Serial.print("ESC"); Serial.print(i); Serial.print(": PWM="); 
     Serial.print(pwm[i]); Serial.print(", Offset="); Serial.println(esc_offset[i]);
   }
   Serial.print("PID: "); Serial.println(pid_enabled ? "ON" : "OFF");
   Serial.println("=== PID Parameters ===");
   Serial.print("Roll: Kp="); Serial.print(roll_pid.kp);
   Serial.print(" Ki="); Serial.print(roll_pid.ki);
   Serial.print(" Kd="); Serial.println(roll_pid.kd);
   Serial.print("Pitch: Kp="); Serial.print(pitch_pid.kp);
   Serial.print(" Ki="); Serial.print(pitch_pid.ki);
   Serial.print(" Kd="); Serial.println(pitch_pid.kd);
   Serial.print("Yaw: Kp="); Serial.print(yaw_pid.kp);
   Serial.print(" Ki="); Serial.print(yaw_pid.ki);
   Serial.print(" Kd="); Serial.println(yaw_pid.kd);
   Serial.println("=== Target Angles ===");
   Serial.print("Roll Target: "); Serial.print(roll_pid.setpoint); Serial.println(" deg");
   Serial.print("Pitch Target: "); Serial.print(pitch_pid.setpoint); Serial.println(" deg");
   Serial.print("Yaw Target: "); Serial.print(yaw_pid.setpoint); Serial.println(" deg/s");
   Serial.println("=== Other Parameters ===");
   Serial.print("Angle Deadband: "); Serial.print(angle_deadband); Serial.println(" deg");
   Serial.print("Min Correction: "); Serial.print(min_correction); Serial.println(" us");
   Serial.print("Max Correction: "); Serial.print(max_correction); Serial.println(" us");
   Serial.print("PID Scale Factor: "); Serial.println(pid_scale_factor);
   Serial.print("Min Motor Output: "); Serial.print(min_motor_output); Serial.println(" us");
   Serial.print("Base Throttle: "); Serial.println(base_throttle);
   Serial.print("I-term Limit: "); Serial.println(i_limit);
   Serial.println("=== Current Attitude ===");
   Serial.print("Roll: "); Serial.print(roll_angle);
   Serial.print(" Pitch: "); Serial.print(pitch_angle);
   Serial.print(" Yaw: "); Serial.println(filter.getYaw());
   return;
 }

 /* 任意 4 値 --------------------------------------------------------- */
 else {
   uint16_t p0,p1,p2,p3;
   if (sscanf(cmd, "%hu %hu %hu %hu", &p0,&p1,&p2,&p3) == 4) {
     pwm[0]=p0; pwm[1]=p1; pwm[2]=p2; pwm[3]=p3;
   } else return;              // 無効文字列は無視
 }


 writeNow();
 landing = false;

}


/* ---------- I²C 受信 ---------- */
void onReceive(int) {
 idx = 0;
 while (Wire.available() && idx < sizeof(buf) - 1) {
   char c = Wire.read();
   if (c >= 32 && c <= 126) buf[idx++] = c;
 }
 buf[idx] = '\0';
 applyCmd(buf);
}


/* ---------- セットアップ ---------- */
void setup() {
 Serial.begin(115200);  // シリアル通信開始
 Serial.println("ESC Controller with PID Started");
 
 // IMU初期化
 if (imu.begin() != 0) {
   Serial.println("IMU initialization failed!");
 } else {
   Serial.println("IMU initialized successfully");
 }
 
 // Madgwickフィルター初期化
 filter.begin(50.0);  // 50Hz サンプリングレート
 Serial.println("Madgwick filter initialized");

 for (byte i = 0; i < 4; i++) esc[i].attach(escPin[i], ESC_MIN, ESC_MAX);
 stopAll();
 delay(2000);                 // ESC arming
 Wire.begin(SLAVE_ADDR);
 Wire.onReceive(onReceive);
}


/* ---------- LOOP ---------- */
void loop() {
  applyPIDControl();  // PID制御を連続実行
  delay(1);           // 短いディレイ
}


