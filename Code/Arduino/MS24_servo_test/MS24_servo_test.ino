#include <Servo.h>

Servo Y_SERVO;
Servo X_SERVO;

const int X_SERVO_PIN = 9;
const int Y_SERVO_PIN = 10;

const int X_NEG_PIN = 2;
const int X_POS_PIN = 3;
const int Y_NEG_PIN = 12;
const int Y_POS_PIN = 13;

const int increment_amount = 1;

#define X_MIN 60
#define X_MAX 110
#define Y_MIN 60
#define Y_MAX 110
int X_SERVO_ANGLE = 84;
int Y_SERVO_ANGLE = 83;


int servo_angle = 90;

void setup() {
  Y_SERVO.attach(Y_SERVO_PIN);
  Y_SERVO.write(Y_SERVO_ANGLE);

  X_SERVO.attach(X_SERVO_PIN);
  X_SERVO.write(X_SERVO_ANGLE);

  pinMode(X_NEG_PIN, INPUT_PULLUP);
  pinMode(X_POS_PIN, INPUT_PULLUP);
  pinMode(Y_NEG_PIN, INPUT_PULLUP);
  pinMode(Y_POS_PIN, INPUT_PULLUP);

  Serial.begin(9600);
}

void loop() {

  if (digitalRead(X_NEG_PIN) == 0)
  {
    X_SERVO_ANGLE -= increment_amount;
    X_SERVO.write(X_SERVO_ANGLE);
  }
  else if (digitalRead(X_POS_PIN) == 0)
  {
    X_SERVO_ANGLE += increment_amount;
    X_SERVO.write(X_SERVO_ANGLE);
  }
  else if (digitalRead(Y_NEG_PIN) == 0)
  {
    Y_SERVO_ANGLE -= increment_amount;
    Y_SERVO.write(Y_SERVO_ANGLE);
  }
  else if (digitalRead(Y_POS_PIN) == 0)
  {
    Y_SERVO_ANGLE += increment_amount;
    Y_SERVO.write(Y_SERVO_ANGLE);
  }


  Serial.print("X: ");
  Serial.println(X_SERVO_ANGLE);
  Serial.print("Y: ");
  Serial.println(Y_SERVO_ANGLE);

  Serial.println("");

  delay(250);
}