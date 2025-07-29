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


#define SLAVE_ADDR 0x08
#define ESC_MIN    1000
#define ESC_MAX    2000
#define HOVER_THR  1450          // ホバリング推力
#define LAND_THR   1250          // 降下推力
#define DELTA_XY   10
#define DELTA_Z    10
#define RAMP_STEP  10            // 1 ステップあたりの増分 (µs)
#define RAMP_DELAY 15            // ステップ間ウエイト (ms)

// PID制御パラメータ
#define PID_RATE   20            // PID制御周期 (ms)
#define MAX_CORRECTION 100       // 最大PID補正値 (µs)

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

// PIDコントローラー
PIDController roll_pid  = {2.0, 0.1, 0.5, 0, 0, 0, 0};
PIDController pitch_pid = {2.0, 0.1, 0.5, 0, 0, 0, 0};
PIDController yaw_pid   = {1.5, 0.05, 0.3, 0, 0, 0, 0};

// 姿勢データ
float roll_angle = 0, pitch_angle = 0, yaw_rate = 0;
bool pid_enabled = false;
unsigned long last_pid_time = 0;


char buf[40];  byte idx = 0;
bool landing = false;            // STOP1 → true
uint16_t pwm[4] = {ESC_MIN, ESC_MIN, ESC_MIN, ESC_MIN}; // 常に現在値を保持



/* ---------- IMU読み取り ---------- */
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

/* ---------- PID計算 ---------- */
float calculatePID(PIDController* pid, float input, float dt) {
  float error = pid->setpoint - input;
  
  // 積分項
  pid->integral += error * dt;
  pid->integral = constrain(pid->integral, -50, 50); // 積分ワインドアップ防止
  
  // 微分項
  float derivative = (error - pid->previous_error) / dt;
  
  // PID出力
  float output = pid->kp * error + pid->ki * pid->integral + pid->kd * derivative;
  
  pid->previous_error = error;
  return constrain(output, -MAX_CORRECTION, MAX_CORRECTION);
}

/* ---------- PID制御適用 ---------- */
void applyPIDControl() {
  if (!pid_enabled) return;
  
  unsigned long current_time = millis();
  if (current_time - last_pid_time < PID_RATE) return;
  
  float dt = (current_time - last_pid_time) / 1000.0;
  last_pid_time = current_time;
  
  readIMU();
  
  // PID計算
  float roll_correction = calculatePID(&roll_pid, roll_angle, dt);
  float pitch_correction = calculatePID(&pitch_pid, pitch_angle, dt);
  float yaw_correction = calculatePID(&yaw_pid, yaw_rate, dt);
  
  // モーター配置：
  // 0: 前左, 1: 前右, 2: 後左, 3: 後右
  int16_t motor_correction[4];
  
  // Roll制御（左右傾き）
  motor_correction[0] = -roll_correction; // 前左
  motor_correction[1] = +roll_correction; // 前右
  motor_correction[2] = -roll_correction; // 後左
  motor_correction[3] = +roll_correction; // 後右
  
  // Pitch制御（前後傾き）
  motor_correction[0] += -pitch_correction; // 前左
  motor_correction[1] += -pitch_correction; // 前右
  motor_correction[2] += +pitch_correction; // 後左
  motor_correction[3] += +pitch_correction; // 後右
  
  // Yaw制御（回転）
  motor_correction[0] += +yaw_correction; // 前左
  motor_correction[1] += -yaw_correction; // 前右
  motor_correction[2] += -yaw_correction; // 後左
  motor_correction[3] += +yaw_correction; // 後右
  
  // PWM値に補正を適用
  for (byte i = 0; i < 4; i++) {
    pwm[i] = constrain(pwm[i] + motor_correction[i], ESC_MIN, ESC_MAX);
  }
  
  writeNow();
}

/* ---------- 低レベル ---------- */
void writeNow() {
 for (byte i = 0; i < 4; i++) {
   uint16_t pw = constrain(pwm[i], ESC_MIN, ESC_MAX);
   esc[i].writeMicroseconds(pw);
   pwm[i] = pw;
   Serial.print("ESC"); Serial.print(i);
   Serial.print("="); Serial.print(pw); Serial.print("\n");
 }
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
   rampTo(HOVER_THR);          // 現在値→1450 µs へ滑らかに変化
   landing = false;
   pid_enabled = true;         // PID制御開始
   last_pid_time = millis();
   return;
 }


 /* STOP --------------------------------------------------------------- */
 if (!strcmp(cmd, "STOP")) {
   if (!landing) {             // 1 回目：降下推力で保持
     rampTo(LAND_THR);
     landing = true;
   } else {                    // 2 回目：完全停止
     stopAll();
     landing = false;
     pid_enabled = false;      // PID制御停止
   }
   return;
 }


 /* 方向 / 上下 -------------------------------------------------------- */
 if      (!strcmp(cmd,"FWD"))  {pwm[0]-=DELTA_XY; pwm[1]-=DELTA_XY; pwm[2]+=DELTA_XY; pwm[3]+=DELTA_XY;}
 else if (!strcmp(cmd,"BACK")) {pwm[0]+=DELTA_XY; pwm[1]+=DELTA_XY; pwm[2]-=DELTA_XY; pwm[3]-=DELTA_XY;}
 else if (!strcmp(cmd,"LEFT")) {pwm[0]-=DELTA_XY; pwm[1]+=DELTA_XY; pwm[2]-=DELTA_XY; pwm[3]+=DELTA_XY;}
 else if (!strcmp(cmd,"RIGHT")){pwm[0]+=DELTA_XY; pwm[1]-=DELTA_XY; pwm[2]+=DELTA_XY; pwm[3]-=DELTA_XY;}
 else if (!strcmp(cmd,"UP"))   {for(byte i=0;i<4;i++) pwm[i]+=DELTA_Z;}
 else if (!strcmp(cmd,"DOWN")) {for(byte i=0;i<4;i++) pwm[i]-=DELTA_Z;}
 else if (!strcmp(cmd,"PALALEL")){for(byte i=0;i<4;i++) pwm[i]=HOVER_THR;}
 else if (!strcmp(cmd,"PID_ON")) {pid_enabled = true; last_pid_time = millis();}
 else if (!strcmp(cmd,"PID_OFF")) {pid_enabled = false;}


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


