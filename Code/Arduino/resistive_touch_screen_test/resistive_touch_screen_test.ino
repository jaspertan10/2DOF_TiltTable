// =============================
// Resistive touch test selector
// =============================

// Uncomment ONE of these:
//#define TEST_X
#define TEST_Y

const int Yup   = A0;
const int Ydown = A1;
const int Xle   = A2;
const int Xri   = A3;

void setup() {
  Serial.begin(9600);

#ifdef TEST_X
  // Drive Y axis: top = 5V, bottom = 0V
  pinMode(Yup, OUTPUT);
  pinMode(Ydown, OUTPUT);
  digitalWrite(Yup, HIGH);
  digitalWrite(Ydown, LOW);

  // X axis floats, measure from Xle
  pinMode(Xle, INPUT);
  pinMode(Xri, INPUT);

  Serial.println("TEST_X mode: measuring X position");
#endif

#ifdef TEST_Y
  // Drive X axis: left = 0V, right = 5V
  pinMode(Xle, OUTPUT);
  pinMode(Xri, OUTPUT);
  digitalWrite(Xle, LOW);
  digitalWrite(Xri, HIGH);

  // Y axis floats, measure from Yup
  pinMode(Yup, INPUT);
  pinMode(Ydown, INPUT);

  Serial.println("TEST_Y mode: measuring Y position");
#endif
}

void loop() {
#ifdef TEST_X
  int value = analogRead(Xle);
  Serial.print("X Position: ");
  Serial.println(value);
#endif

#ifdef TEST_Y
  int value = analogRead(Yup);
  Serial.print("Y Position: ");
  Serial.println(value);
#endif

  delay(100);
}