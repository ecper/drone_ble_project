/*
* Quad ESC Controller v7 with PID Control
*  RUN  : Current value to HOVER_THR with smooth acceleration (ramp up)
*  STOP : First press LAND_THR for descent hold, second press ESC_MIN for complete stop
*  Direction/UP/DOWN/PARALLEL : Immediate thrust change and hold
*  Attitude stabilization with PID control
*/


#include <Wire.h>
#include <Servo.h>
#include <LSM6DS3.h>
#include <MadgwickAHRS.h>


#define SLAVE_ADDR 0x08
#define ESC_MIN    1000
#define ESC_MAX    2000
#define HOVER_THR  1250          // Hovering thrust
#define LAND_THR   1250          // Landing thrust
#define DELTA_XY   10
#define DELTA_Z    10
#define RAMP_STEP  10            // Increment per step (µs)
#define RAMP_DELAY 15            // Wait between steps (ms)

// PID control parameter
#define PID_RATE   20            // PID control period (ms)

// Dynamically adjustable parameters (based on reference code)
float angle_deadband = 0.5;      // Angle deadband (degrees) - ignore 1 degree or less
int16_t min_correction = 5;      // Minimum correction value (µs) - enables fine adjustments
int16_t max_correction = 100;    // Maximum PID correction value (µs) - increased based on reference code

// PID scaling parameters (from reference code)
float pid_scale_factor = 0.5;   // PID output scaling (1.0 uses as-is)
int16_t min_motor_output = 50;   // Minimum motor output guarantee (ESC_MIN + this value)
float i_limit = 25.0;           // Integral term limit value
bool use_gyro_for_derivative = true;  // D-term implementation method (true: use gyro, false: use error derivative)

// PID structure
struct PIDController {
  float kp, ki, kd;
  float previous_error;
  float integral;
  float setpoint;
  unsigned long last_time;
};

// Sensor and ESC
LSM6DS3 imu(I2C_MODE, 0x6A);
Servo esc[4];
const uint8_t escPin[4] = {0, 1, 2, 3};

// Madgwick filter
Madgwick filter;

// PID controllers (reference code based values)
PIDController roll_pid  = {3.0, 0.0, 0.3, 0, 0, 0, 0};   // Reference code standard value
PIDController pitch_pid = {3.0, 0.0, 1.2, 0, 0, 0, 0};   // Reference code standard value
PIDController yaw_pid   = {0.0, 0.0, 0.0, 0, 0, 0, 0};   // Yaw is slightly conservative

// Attitude data (improved version)
float roll_angle = 0, pitch_angle = 0, yaw_rate = 0;
float roll_gyro = 0, pitch_gyro = 0, yaw_gyro = 0;  // Gyro value addition
bool pid_enabled = false;
unsigned long last_pid_time = 0;

// Base thrust management
uint16_t base_throttle = HOVER_THR;  // Base thrust

// ESC individual adjustment offset
int16_t esc_offset[4] = {0, -60, -0, -60};  // Each ESC correction value (FR, BL, BR, FL)


char buf[40];  byte idx = 0;
bool landing = false;            // STOP 1 becomes true
uint16_t pwm[4] = {ESC_MIN, ESC_MIN, ESC_MIN, ESC_MIN}; // Always keep current values



/* ---------- PID reset ---------- */
void resetPID() {
  // Set target angle to 0
  roll_pid.setpoint = 0.0;
  pitch_pid.setpoint = 0.0;
  yaw_pid.setpoint = 0.0;
  
  // Reset integral term
  roll_pid.integral = 0.0;
  pitch_pid.integral = 0.0;
  yaw_pid.integral = 0.0;
  
  // Reset previous error as well
  roll_pid.previous_error = 0.0;
  pitch_pid.previous_error = 0.0;
  yaw_pid.previous_error = 0.0;
}

/* ---------- IMU read (Madgwick filter version) ---------- */
void readIMU() {
  float ax = imu.readFloatAccelX();
  float ay = imu.readFloatAccelY();
  float az = imu.readFloatAccelZ();
  
  float gx = imu.readFloatGyroX();
  float gy = imu.readFloatGyroY();
  float gz = imu.readFloatGyroZ();
  
  // Original angle calculation method (for comparison when Madgwick doesn't work)
  float roll_from_accel = atan2(ay, az) * 180 / PI;
  float pitch_from_accel = atan2(-ax, sqrt(ay*ay + az*az)) * 180 / PI;
  
  // Update attitude with Madgwick filter (6-axis without magnetic sensor)
  // Pass 0 for magnetic sensor data
  filter.update(gx, gy, gz, ax, ay, az, 0, 0, 0);
  
  // Get angles from filter
  // Temporarily use accelerometer-based angles (when Madgwick doesn't behave)
  roll_angle = roll_from_accel;  // filter.getRoll();
  pitch_angle = pitch_from_accel; // filter.getPitch();
  float yaw_angle = filter.getYaw();  // Yaw angle (when using)
  
  // Debug output: comparison of accelerometer calculation and Madgwick output
  static unsigned long lastDebugTime = 0;
  if (millis() - lastDebugTime > 500) {  // Output every 500ms
    lastDebugTime = millis();
    Serial.print("Accel angles - R: "); Serial.print(roll_from_accel);
    Serial.print(" P: "); Serial.print(pitch_from_accel);
    Serial.print(" | Madgwick - R: "); Serial.print(roll_angle);
    Serial.print(" P: "); Serial.println(pitch_angle);
  }
  
  // Save gyro values as well (for PID derivative term)
  roll_gyro = gx;   // Roll angular velocity
  pitch_gyro = gy;  // Pitch angular velocity  
  yaw_gyro = gz;    // Yaw angular velocity (used for yaw control)
  yaw_rate = gz;    // For compatibility
}

/* ---------- PID calculation (correct implementation) ---------- */
float calculatePID(PIDController* pid, float input, float gyro_rate, float dt) {
  float error = pid->setpoint - input;
  
  // Deadband processing
  if (abs(error) < angle_deadband) {
    error = 0.0;
  }
  
  // Integral term
  pid->integral += error * dt;
  pid->integral = constrain(pid->integral, -i_limit, i_limit); // Prevent integral windup
  
  // Dynamically select derivative term calculation method
  float derivative;
  if (use_gyro_for_derivative) {
    // Method 1: Direct use of gyro value (faster response, sensitive to noise)
    // Note: Gyro value is angular velocity, so need to invert sign from error
    derivative = -gyro_rate; // Correction with negative sign
  } else {
    // Method 2: Use error change rate (standard PID, smoother)
    derivative = (error - pid->previous_error) / dt;
    // Safety check for case when dt is 0
    if (dt <= 0.001) derivative = 0;
  }
  
  // PID output calculation
  float output = pid->kp * error + pid->ki * pid->integral + pid->kd * derivative;
  
  // Scaling (from reference code)
  output = output * pid_scale_factor;
  
  pid->previous_error = error;
  return constrain(output, -max_correction, max_correction);
}

/* ---------- Apply PID control (improved version) ---------- */
void applyPIDControl() {
  if (!pid_enabled) return;
  
  unsigned long current_time = millis();
  if (current_time - last_pid_time < PID_RATE) return;
  
  float dt = (current_time - last_pid_time) / 1000.0;
  last_pid_time = current_time;
  
  readIMU();
  
  // Debug output (every 500ms)
  static unsigned long lastPIDDebug = 0;
  if (millis() - lastPIDDebug > 500) {
    lastPIDDebug = millis();
    Serial.print("PID Debug - Roll: "); Serial.print(roll_angle);
    Serial.print(" Pitch: "); Serial.print(pitch_angle);
    Serial.print(" Enabled: "); Serial.println(pid_enabled);
  }
  
  // PID calculation (using gyro value as derivative term)
  float roll_correction = calculatePID(&roll_pid, roll_angle, roll_gyro, dt);
  float pitch_correction = calculatePID(&pitch_pid, pitch_angle, pitch_gyro, dt);
  float yaw_correction = calculatePID(&yaw_pid, yaw_rate, yaw_gyro, dt);
  
  // Motor layout:
  // 0: FR (front right), 1: BL (back left), 2: BR (back right), 3: FL (front left)
  
  // Calculate correction amount from base thrust (reference code method)
  float motor_output[4];
  
  // Roll control (strengthen right side motors when tilting right)
  motor_output[0] = base_throttle - roll_correction; // FR
  motor_output[1] = base_throttle + roll_correction; // BL  
  motor_output[2] = base_throttle - roll_correction; // BR
  motor_output[3] = base_throttle + roll_correction; // FL
  
  // Pitch control (strengthen back side motors when tilting forward)
  motor_output[0] += pitch_correction; // FR
  motor_output[1] -= pitch_correction; // BL
  motor_output[2] -= pitch_correction; // BR
  motor_output[3] += pitch_correction; // FL
  
  // Yaw control (strengthen counterclockwise motors to stop clockwise rotation)
  motor_output[0] += yaw_correction; // FR (clockwise)
  motor_output[1] += yaw_correction; // BL (counterclockwise)
  motor_output[2] -= yaw_correction; // BR (clockwise)
  motor_output[3] -= yaw_correction; // FL (counterclockwise)
  
  // Minimum motor output guarantee and range restriction
  for (byte i = 0; i < 4; i++) {
    // Minimum output guarantee
    if (motor_output[i] < ESC_MIN + min_motor_output) {
      motor_output[i] = ESC_MIN + min_motor_output;
    }
    // Maximum value restriction
    pwm[i] = constrain(motor_output[i], ESC_MIN, ESC_MAX);
  }
  
  // Debug output (every 500ms)
  static unsigned long lastCorrectionDebug = 0;
  if (millis() - lastCorrectionDebug > 500) {
    lastCorrectionDebug = millis();
    Serial.print("Corrections - R: "); Serial.print(roll_correction);
    Serial.print(" P: "); Serial.print(pitch_correction);
    Serial.print(" Y: "); Serial.println(yaw_correction);
  }
  
  writeNow();
}

/* ---------- Low level ---------- */
void writeNow() {
 // Debug output control (only when PID enabled)
 static unsigned long lastWriteDebug = 0;
 bool shouldPrint = pid_enabled && (millis() - lastWriteDebug > 1000);
 if (shouldPrint) lastWriteDebug = millis();
 
 for (byte i = 0; i < 4; i++) {
   uint16_t pw = constrain(pwm[i] + esc_offset[i], ESC_MIN, ESC_MAX);
   esc[i].writeMicroseconds(pw);
   pwm[i] = pw - esc_offset[i];  // Keep original value
   
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


/* ---------- Ramp up ---------- */
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


/* ---------- Apply command ---------- */
void applyCmd(const char *cmd) {


 /* RUN ---------------------------------------------------------------- */
 if (!strcmp(cmd, "RUN")) {
   base_throttle = HOVER_THR;   // Set base thrust
   rampTo(HOVER_THR);          // current value to 1450 µs  smoothly
   landing = false;
   pid_enabled = true;         // Begin PID control
   last_pid_time = millis();
   resetPID();                 // Initialize PID parameters
   return;
 }


 /* STOP --------------------------------------------------------------- */
 if (!strcmp(cmd, "STOP")) {
   pid_enabled = false;        // First stop PID control
   // Reset target angle
   roll_pid.setpoint = 0.0;
   pitch_pid.setpoint = 0.0;
   yaw_pid.setpoint = 0.0;
   if (!landing) {             // 1st time: maintain with descent thrust
     rampTo(LAND_THR);
     landing = true;
   } else {                    // 2nd time: complete stop
     stopAll();
     landing = false;
   }
   return;
 }

/* Emergency stop --------------------------------------------------------- */
 else if (!strcmp(cmd,"EMERGENCY") || !strcmp(cmd,"ESTOP")) {
   pid_enabled = false;
   stopAll();
   landing = false;
   Serial.println("EMERGENCY STOP!");
   return;
 }



 /* Direction / Up/Down -------------------------------------------------------- */
 if (!strcmp(cmd,"FWD"))  {
   if (pid_enabled) {
     // When PID control: set target angle（forward lowers the nose）
     pitch_pid.setpoint = -5.0;  // -5 degrees
   } else {
     // When normal control: directly adjust PWM values
     pwm[0]-=DELTA_XY; pwm[1]-=DELTA_XY; pwm[2]+=DELTA_XY; pwm[3]+=DELTA_XY;
   }
 }
 else if (!strcmp(cmd,"BACK")) {
   if (pid_enabled) {
     // When PID control: set target angle（backward raises the nose）
     pitch_pid.setpoint = 5.0;   // +5 degrees
   } else {
     // When normal control: directly adjust PWM values
     pwm[0]+=DELTA_XY; pwm[1]+=DELTA_XY; pwm[2]-=DELTA_XY; pwm[3]-=DELTA_XY;
   }
 }
 else if (!strcmp(cmd,"LEFT")) {
   if (pid_enabled) {
     // When PID control: set target angle（left move tilts to right）
     roll_pid.setpoint = 5.0;    // +5 degrees
   } else {
     // When normal control: directly adjust PWM values
     pwm[0]-=DELTA_XY; pwm[1]+=DELTA_XY; pwm[2]-=DELTA_XY; pwm[3]+=DELTA_XY;
   }
 }
 else if (!strcmp(cmd,"RIGHT")){
   if (pid_enabled) {
     // When PID control: set target angle（right move tilts to left）
     roll_pid.setpoint = -5.0;   // -5 degrees
   } else {
     // When normal control: directly adjust PWM values
     pwm[0]+=DELTA_XY; pwm[1]-=DELTA_XY; pwm[2]+=DELTA_XY; pwm[3]-=DELTA_XY;
   }
 }
 else if (!strcmp(cmd,"UP"))   {
   if (pid_enabled) {
     // When PID control: increase base thrust
     base_throttle = constrain(base_throttle + DELTA_Z, ESC_MIN + min_motor_output, ESC_MAX - max_correction);
   } else {
     // When normal control: increase all thrust
     for(byte i=0;i<4;i++) pwm[i]+=DELTA_Z;
   }
 }
 else if (!strcmp(cmd,"DOWN")) {
   if (pid_enabled) {
     // When PID control: decrease base thrust
     base_throttle = constrain(base_throttle - DELTA_Z, ESC_MIN + min_motor_output, ESC_MAX - max_correction);
   } else {
     // When normal control: decrease all thrust
     for(byte i=0;i<4;i++) pwm[i]-=DELTA_Z;
   }
 }
 else if (!strcmp(cmd,"PALALEL")){
   if (pid_enabled) {
     // When PID control: set target angle to horizontal（0 degrees)
     roll_pid.setpoint = 0.0;
     pitch_pid.setpoint = 0.0;
     yaw_pid.setpoint = 0.0;
   } else {
     // When normal control: set all motors to hovering thrust
     for(byte i=0;i<4;i++) pwm[i]=HOVER_THR;
   }
 }
 else if (!strcmp(cmd,"PID_ON")) {
   pid_enabled = true; 
   last_pid_time = millis();
   resetPID();  // Initialize PID parameters
 }
 else if (!strcmp(cmd,"PID_OFF")) {
   pid_enabled = false;
   // Reset target angle（(keep integral term)）
   roll_pid.setpoint = 0.0;
   pitch_pid.setpoint = 0.0;
   yaw_pid.setpoint = 0.0;
 }
 
 /* ESC individual test ---------------------------------------------------- */
else if (!strcmp(cmd,"TEST0")) {
   pid_enabled = false;  // Disable PID control
   stopAll(); 
   pwm[0]=HOVER_THR;  // ESC0 only hovering thrust
   writeNow();         // Apply change
   return;
 }
 else if (!strcmp(cmd,"TEST1")) {
   pid_enabled = false;
   stopAll(); 
   pwm[1]=HOVER_THR;  // ESC1 only hovering thrust
   writeNow();         // Apply change
   return;
 }
 else if (!strcmp(cmd,"TEST2")) {
   pid_enabled = false;
   stopAll(); 
   pwm[2]=HOVER_THR;  // ESC2 only hovering thrust
   writeNow();         // Apply change
   return;
 }
 else if (!strcmp(cmd,"TEST3")) {
   pid_enabled = false;
   stopAll(); 
   pwm[3]=HOVER_THR;  // ESC3 only hovering thrust
   writeNow();         // Apply change
   return;
 }

 /* ESC offset adjustment ----------------------------------------------- */
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
 
 /* PID parameter settings ------------------------------------------------ */
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
 
 /* Other parameter settings ------------------------------------------- */
 else if (strncmp(cmd, "SET_DEADBAND", 12) == 0) {
   float value;
   if (sscanf(cmd, "SET_DEADBAND %f", &value) == 1) {
     angle_deadband = constrain(value, 0.0, 45.0);  // 0-45 degrees range
     Serial.print("DEADBAND set to: "); Serial.println(angle_deadband);
   }
   return;
 }
 else if (strncmp(cmd, "SET_MIN_CORR", 12) == 0) {
   int value;
   if (sscanf(cmd, "SET_MIN_CORR %d", &value) == 1) {
     min_correction = constrain(value, 0, 100);  // 0-100µs range
     Serial.print("MIN_CORRECTION set to: "); Serial.println(min_correction);
   }
   return;
 }
 else if (strncmp(cmd, "SET_MAX_CORR", 12) == 0) {
   int value;
   if (sscanf(cmd, "SET_MAX_CORR %d", &value) == 1) {
     max_correction = constrain(value, 5, 200);  // 5-200µs range (lower upper limit for safety)
     Serial.print("MAX_CORRECTION set to: "); Serial.println(max_correction);
   }
   return;
 }
 
 /* Simple adjustment command ------------------------------------------------- */
 else if (!strcmp(cmd, "PID_GENTLE")) {
   // More gentle PID settings（(reference code base)）
   roll_pid.kp = 3.0; roll_pid.ki = 0.0; roll_pid.kd = 0.5;
   pitch_pid.kp = 3.0; pitch_pid.ki = 0.0; pitch_pid.kd = 0.5;
   yaw_pid.kp = 2.0; yaw_pid.ki = 0.0; yaw_pid.kd = 0.3;
   pid_scale_factor = 0.5;  // gentle scale
   Serial.println("PID set to GENTLE mode");
   return;
 }
 else if (!strcmp(cmd, "PID_NORMAL")) {
   // Standard PID settings（(reference code base)）
   roll_pid.kp = 6.0; roll_pid.ki = 0.0; roll_pid.kd = 0.8;
   pitch_pid.kp = 6.0; pitch_pid.ki = 0.0; pitch_pid.kd = 0.8;
   yaw_pid.kp = 4.0; yaw_pid.ki = 0.0; yaw_pid.kd = 0.5;
   pid_scale_factor = 1.0;   // standard scale (as-is)
   Serial.println("PID set to NORMAL mode");
   return;
 }
 else if (!strcmp(cmd, "PID_AGGRESSIVE")) {
   // More aggressive PID settings（for advanced users）
   roll_pid.kp = 10.0; roll_pid.ki = 0.1; roll_pid.kd = 1.2;
   pitch_pid.kp = 10.0; pitch_pid.ki = 0.1; pitch_pid.kd = 1.2;
   yaw_pid.kp = 6.0; yaw_pid.ki = 0.05; yaw_pid.kd = 0.8;
   pid_scale_factor = 1.5;  // larger scale
   Serial.println("PID set to AGGRESSIVE mode");
   return;
 }
 
 /* Detail parameter adjustment ------------------------------------------- */
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
 
 /* D-term implementation method switching -------------------------------------------- */
 else if (!strcmp(cmd, "D_GYRO")) {
   // Switch to gyro-based D-term
   use_gyro_for_derivative = true;
   Serial.println("Derivative method: GYRO (faster response)");
   return;
 }
 else if (!strcmp(cmd, "D_ERROR")) {
   // Switch to error derivative-based D-term
   use_gyro_for_derivative = false;
   Serial.println("Derivative method: ERROR_DIFF (smoother)");
   return;
 }
 
 /* Show settings --------------------------------------------------------- */
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
   Serial.println("=== Derivative Method ===");
   Serial.print("Using: "); Serial.println(use_gyro_for_derivative ? "GYRO" : "ERROR_DIFF");
   Serial.println("=== Current Attitude ===");
   Serial.print("Roll: "); Serial.print(roll_angle);
   Serial.print(" Pitch: "); Serial.print(pitch_angle);
   Serial.print(" Yaw: "); Serial.println(filter.getYaw());
   return;
 }

 /* Arbitrary 4 values --------------------------------------------------------- */
 else {
   uint16_t p0,p1,p2,p3;
   if (sscanf(cmd, "%hu %hu %hu %hu", &p0,&p1,&p2,&p3) == 4) {
     pwm[0]=p0; pwm[1]=p1; pwm[2]=p2; pwm[3]=p3;
   } else return;              // Ignore disabled string
 }


 writeNow();
 landing = false;

}


/* ---------- I2C receive ---------- */
void onReceive(int) {
 idx = 0;
 while (Wire.available() && idx < sizeof(buf) - 1) {
   char c = Wire.read();
   if (c >= 32 && c <= 126) buf[idx++] = c;
 }
 buf[idx] = '\0';
 applyCmd(buf);
}


/* ---------- Setup ---------- */
void setup() {
 Serial.begin(115200);  // Begin serial communication
 Serial.println("ESC Controller with PID Started");
 
 // IMU initialize
 if (imu.begin() != 0) {
   Serial.println("IMU initialization failed!");
 } else {
   Serial.println("IMU initialized successfully");
 }
 
 // Madgwick filter initialize
 filter.begin(50.0);  // 50Hz sampling rate
 Serial.println("Madgwick filter initialized");

 for (byte i = 0; i < 4; i++) esc[i].attach(escPin[i], ESC_MIN, ESC_MAX);
 stopAll();
 delay(2000);                 // ESC arming
 Wire.begin(SLAVE_ADDR);
 Wire.onReceive(onReceive);
}


/* ---------- LOOP ---------- */
void loop() {
  applyPIDControl();  // PID control continuous execution
  delay(1);           // short delay
}


