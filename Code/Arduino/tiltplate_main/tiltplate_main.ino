#include <Servo.h>

#define DEBUG_PRINT_MS 250

Servo Y_SERVO;
Servo X_SERVO;

int counter = 0;

// Pinouts
const int X_SERVO_PIN        = 9;
const int Y_SERVO_PIN        = 10;
const int TILT_Y_UP_PIN      = A0;
const int TILT_Y_DOWN_PIN    = A1;
const int TILT_X_LEFT_PIN    = A2;
const int TILT_X_RIGHT_PIN   = A3;

const int X_SERVO_STARTING_POS = 84;
const int Y_SERVO_STARTING_POS = 83;
const int TILT_X_MIDDLE_POS    = 240;
const int TILT_Y_MIDDLE_POS    = 500;

// PID gains
float KpX = 0.045;
float KpY = 0.045;
float KiX = 0.01;
float KiY = 0.01;
float KdX = 0.03;
float KdY = 0.03;

// Servo Angles
int X_SERVO_CENTER = 84;
int Y_SERVO_CENTER = 83;
int X_SERVO_MIN = 74;
int X_SERVO_MAX = 94;
int Y_SERVO_MIN = 73;
int Y_SERVO_MAX = 93;

int setpoint_x_pos = TILT_X_MIDDLE_POS;
int setpoint_y_pos = TILT_Y_MIDDLE_POS;

const int LOOP_PERIOD_MS = 10; // 10 = 100 Hz
unsigned long lastLoopTime = 0;
unsigned long lastDebugTime = 0;

// Valid reading windows
const int X_ADC_VALID_MIN = 40;
const int X_ADC_VALID_MAX = 550;
const int Y_ADC_VALID_MIN = 120;
const int Y_ADC_VALID_MAX = 900;

// Max allowed jump per loop
const int X_MAX_STEP = 80;
const int Y_MAX_STEP = 100;

// Last known good readings
int lastGoodX = TILT_X_MIDDLE_POS;
int lastGoodY = TILT_Y_MIDDLE_POS;

// Last errors for derivative term
float lastErrorX = 0.0;
float lastErrorY = 0.0;

// Integral terms
float integralX = 0.0;
float integralY = 0.0;

// Integral accumulates when error is within this band
// No reset-to-zero near setpoint — integral holds its value to correct steady state bias
const float INTEGRAL_ACTIVE_BAND = 60.0;

// Anti-windup clamp
const float INTEGRAL_LIMIT_X = 5000.0;
const float INTEGRAL_LIMIT_Y = 5000.0;

// Derivative low pass filter
// 0.0 = fully frozen, 1.0 = no filter (raw), 0.15 is a good starting point
const float D_FILTER_ALPHA = 0.15;
float dFilterX = 0.0;
float dFilterY = 0.0;

// Counts number of bad reads — if exceeds 6 (ball picked up), reset integral
int badReadCounter = 0;

// Operating mode variables
bool operating_mode_initialized = false;
unsigned long mode_timer = 0;
const int mode_initialize_time_ms = 3000;

typedef enum {
  SET_POINT,
  SQUARE,
  CIRCLE
} operating_mode_t;

operating_mode_t operating_mode = SET_POINT;

// Square mode
int square_points_x[4] = {350, 120, 120, 350};
int square_points_y[4] = {670, 670, 350, 350};
int square_current_point = 0;

// Circle mode
float circle_angle = 0.0;
const float CIRCLE_RADIUS_X = 50.0;
const float CIRCLE_RADIUS_Y = 80; //Plate is taller than wide, therefore X radius needs to be smaller than Y
const float CIRCLE_SPEED    = 0.025;  // radians per loop

// String containing serial input data
String serialBuffer = "";

// Function declarations
int readXPos();
int readYPos();
bool xReadingInRange(int x);
bool yReadingInRange(int y);
void parseSerial();
void handleCommand(String cmd);

void change_operating_mode(operating_mode_t new_mode)
{
  if (new_mode != SET_POINT)
  {
    mode_timer = millis();
  }
  operating_mode = new_mode;
  operating_mode_initialized = false;
}

void setup()
{
  X_SERVO.attach(X_SERVO_PIN);
  Y_SERVO.attach(Y_SERVO_PIN);

  X_SERVO.write(X_SERVO_STARTING_POS);
  Y_SERVO.write(Y_SERVO_STARTING_POS);

  Serial.begin(115200);
}

void loop()
{
  parseSerial();

  if (millis() - lastLoopTime < LOOP_PERIOD_MS) return;
  lastLoopTime = millis();

  // Fixed dt in seconds
  const float dt = LOOP_PERIOD_MS / 1000.0;

  // Raw reads
  int rawX = readXPos();
  int rawY = readYPos();

  // Start filtered values as raw
  int filtX = rawX;
  int filtY = rawY;

  // Range checks
  bool xRangeValid = xReadingInRange(rawX);
  bool yRangeValid = yReadingInRange(rawY);

  // Jump checks
  bool xJumpValid = abs(rawX - lastGoodX) <= X_MAX_STEP;
  bool yJumpValid = abs(rawY - lastGoodY) <= Y_MAX_STEP;

  // If ball has been picked up, allow new position and reset integral
  if (badReadCounter >= 6)
  {
    xJumpValid = true;
    yJumpValid = true;
    integralX  = 0.0;
    integralY  = 0.0;
  }

  bool xValid   = xRangeValid && xJumpValid;
  bool yValid   = yRangeValid && yJumpValid;
  bool goodRead = xValid && yValid;

  // ── Operating modes ──────────────────────────────────────────────────────

  if (operating_mode == SQUARE)
  {
    if (!operating_mode_initialized)
    {
      // Hold middle until ball settles
      setpoint_x_pos = TILT_X_MIDDLE_POS;
      setpoint_y_pos = TILT_Y_MIDDLE_POS;

      if (millis() - mode_timer >= mode_initialize_time_ms)
      {
        operating_mode_initialized = true;
        square_current_point = 0;
        setpoint_x_pos = square_points_x[square_current_point];
        setpoint_y_pos = square_points_y[square_current_point];
        mode_timer = millis();
      }
    }
    else
    {
      if (millis() - mode_timer >= mode_initialize_time_ms)
      {
        square_current_point = (square_current_point + 1) % 4;
        setpoint_x_pos = square_points_x[square_current_point];
        setpoint_y_pos = square_points_y[square_current_point];
        mode_timer = millis();
      }
    }
  }
  if (operating_mode == CIRCLE)
  {
    if (!operating_mode_initialized)
    {
      // Hold middle until ball settles
      setpoint_x_pos = TILT_X_MIDDLE_POS;
      setpoint_y_pos = TILT_Y_MIDDLE_POS;

      if (millis() - mode_timer >= mode_initialize_time_ms)
      {
        operating_mode_initialized = true;
        circle_angle = 0.0;
        mode_timer = millis();
      }
    }
    else
    {
      circle_angle += CIRCLE_SPEED;
      if (circle_angle >= TWO_PI) circle_angle -= TWO_PI;

      setpoint_x_pos = TILT_X_MIDDLE_POS + CIRCLE_RADIUS_X * cos(circle_angle);
      setpoint_y_pos = TILT_Y_MIDDLE_POS + CIRCLE_RADIUS_Y * sin(circle_angle);
    }
  }

  // ── Sensor filtering ─────────────────────────────────────────────────────

  if (goodRead)
  {
    lastGoodX = rawX;
    lastGoodY = rawY;
    badReadCounter = 0;
  }
  else
  {
    filtX = lastGoodX;
    filtY = lastGoodY;
  }

  // ── PID ──────────────────────────────────────────────────────────────────

  float errorX = setpoint_x_pos - filtX;
  float errorY = setpoint_y_pos - filtY;

  // Integral — accumulates within active band
  // No zero-reset near setpoint so accumulated value holds against steady state bias
  if (goodRead && abs(errorX) <= INTEGRAL_ACTIVE_BAND)
  {
    integralX += errorX * dt;
  }
  if (goodRead && abs(errorY) <= INTEGRAL_ACTIVE_BAND)
  {
    integralY += errorY * dt;
  }

  // Anti-windup clamp
  if (integralX >  INTEGRAL_LIMIT_X) integralX =  INTEGRAL_LIMIT_X;
  if (integralX < -INTEGRAL_LIMIT_X) integralX = -INTEGRAL_LIMIT_X;
  if (integralY >  INTEGRAL_LIMIT_Y) integralY =  INTEGRAL_LIMIT_Y;
  if (integralY < -INTEGRAL_LIMIT_Y) integralY = -INTEGRAL_LIMIT_Y;

  // Derivative — low pass filtered to reduce noise spikes
  float rawDX = (errorX - lastErrorX) / dt;
  float rawDY = (errorY - lastErrorY) / dt;

  dFilterX = D_FILTER_ALPHA * rawDX + (1.0 - D_FILTER_ALPHA) * dFilterX;
  dFilterY = D_FILTER_ALPHA * rawDY + (1.0 - D_FILTER_ALPHA) * dFilterY;

  float dErrorX = dFilterX;
  float dErrorY = dFilterY;

  // PID output
  float outputX = KpX * errorX + KiX * integralX + KdX * dErrorX;
  float outputY = KpY * errorY + KiY * integralY + KdY * dErrorY;

  // Save errors for next loop
  lastErrorX = errorX;
  lastErrorY = errorY;

  // Servo commands
  int xServoCmd = X_SERVO_CENTER + outputX;
  int yServoCmd = Y_SERVO_CENTER - outputY;

  xServoCmd = constrain(xServoCmd, X_SERVO_MIN, X_SERVO_MAX);
  yServoCmd = constrain(yServoCmd, Y_SERVO_MIN, Y_SERVO_MAX);

  X_SERVO.write(xServoCmd);
  Y_SERVO.write(yServoCmd);

  // ── Debug output ─────────────────────────────────────────────────────────

  Serial.print("T: "); Serial.print(counter);
  Serial.print(" X: ");     Serial.print(filtX);
  Serial.print(" Y: ");     Serial.print(filtY);
  Serial.print(" Set Point X: "); Serial.print(setpoint_x_pos);
  counter++;

  if (millis() - lastDebugTime >= DEBUG_PRINT_MS)
  {
    lastDebugTime = millis();

#if 0
    Serial.print(" X: ");     Serial.print(filtX);
    Serial.print(" Y: ");     Serial.print(filtY);
    Serial.print(" errX: ");  Serial.print(errorX);
    Serial.print(" errY: ");  Serial.print(errorY);
    Serial.print(" intX: ");  Serial.print(integralX);
    Serial.print(" intY: ");  Serial.print(integralY);
    Serial.print(" dErrX: "); Serial.print(dErrorX);
    Serial.print(" dErrY: "); Serial.print(dErrorY);
    Serial.print(" xCmd: ");  Serial.print(xServoCmd);
    Serial.print(" yCmd: ");  Serial.print(yServoCmd);
#endif

    if (!goodRead)
    {
      //Serial.print("  [BAD READ REPLACED]");
      badReadCounter++;
    }

    Serial.println();
  }
}

// ── Sensor read functions ────────────────────────────────────────────────

int readXPos()
{
  pinMode(TILT_Y_UP_PIN, OUTPUT);
  pinMode(TILT_Y_DOWN_PIN, OUTPUT);
  digitalWrite(TILT_Y_UP_PIN, HIGH);
  digitalWrite(TILT_Y_DOWN_PIN, LOW);

  pinMode(TILT_X_LEFT_PIN, INPUT);
  pinMode(TILT_X_RIGHT_PIN, INPUT);

  delayMicroseconds(300);
  analogRead(TILT_X_LEFT_PIN); // discard first sample

  long sum = 0;
  for (int i = 0; i < 5; i++) {
    sum += analogRead(TILT_X_LEFT_PIN);
  }

  return sum / 5;
}

int readYPos()
{
  pinMode(TILT_X_LEFT_PIN, OUTPUT);
  pinMode(TILT_X_RIGHT_PIN, OUTPUT);
  digitalWrite(TILT_X_LEFT_PIN, LOW);
  digitalWrite(TILT_X_RIGHT_PIN, HIGH);

  pinMode(TILT_Y_UP_PIN, INPUT);
  pinMode(TILT_Y_DOWN_PIN, INPUT);

  delayMicroseconds(300);
  analogRead(TILT_Y_UP_PIN); // discard first sample

  long sum = 0;
  for (int i = 0; i < 5; i++) {
    sum += analogRead(TILT_Y_UP_PIN);
  }

  return sum / 5;
}

bool xReadingInRange(int x)
{
  return (x >= X_ADC_VALID_MIN && x <= X_ADC_VALID_MAX);
}

bool yReadingInRange(int y)
{
  return (y >= Y_ADC_VALID_MIN && y <= Y_ADC_VALID_MAX);
}

// ── Serial parser ────────────────────────────────────────────────────────

void parseSerial()
{
  while (Serial.available())
  {
    char c = Serial.read();
    if (c == '\n')
    {
      serialBuffer.trim();
      if (serialBuffer.length() > 0)
      {
        handleCommand(serialBuffer);
      }
      serialBuffer = "";
    }
    else
    {
      serialBuffer += c;
    }
  }
}

void handleCommand(String cmd)
{
  int sep = cmd.indexOf(':');
  if (sep == -1) return;

  String key = cmd.substring(0, sep);
  float val  = cmd.substring(sep + 1).toFloat();

  if      (key == "KPX")  KpX = val;
  else if (key == "KIX")  KiX = val;
  else if (key == "KDX")  KdX = val;
  else if (key == "KPY")  KpY = val;
  else if (key == "KIY")  KiY = val;
  else if (key == "KDY")  KdY = val;
  else if (key == "SETX") setpoint_x_pos = (int)val;
  else if (key == "SETY") setpoint_y_pos = (int)val;
  else if (key == "MODE") change_operating_mode((operating_mode_t)(int)val);
  else
  {
    Serial.print("Unknown Command: ");
    Serial.println(cmd);
    return;
  }

  Serial.print("ACK: ");
  Serial.println(cmd);
}
