// set pin numbers:

//output 1,5,3,4
//int lampe [] = {
//  9, 10, 8, 11, 7, 12, 6, 13, 22, 21, 24, 20, 26, 19, 28, 18, 32, 30, 36, 34, 40, 38, 44, 42, 33, 31, 37, 35, 41, 39, 45, 43};

static const int FAN_PIN = 9;
static const int PARACHUTE_PIN = 10;
static const int WATERSPLASHER_PIN = 8;
static const int ZERO_CROSSING_INTERRUPT = 1;

volatile int numCrossing = 0;
volatile int numTenPack = 0;
volatile int speedPercentage = 0;

void setup() {
  Serial.begin(9600);

  pinMode(FAN_PIN, OUTPUT);
  pinMode(PARACHUTE_PIN, OUTPUT);
  pinMode(WATERSPLASHER_PIN, OUTPUT);

  // Setup interrupt on supply zero-crossing
  attachInterrupt(ZERO_CROSSING_INTERRUPT, zero_cross_detect, RISING);
}

int readFromSerial() {
  while(Serial.available() < 1){
    ;
  }
  return Serial.read();
}

void loop()
{
  int messageStart = 0;
  int command = 0;
  int value = 0;

  // Protocol: Start each message with 255 (= 0xFF)
  do
    messageStart = readFromSerial();
  while (messageStart != 0xFF);

  do {
    command = readFromSerial();
    value = readFromSerial();
  } while (value == 0xFF);

  switch(command) {
  case 'F':
    Serial.write('F');
    Serial.write(value);
    speedPercentage = value;
    break;
  case 'P':
    Serial.write('P');
    Serial.write(value);
    if (value == 1)
      digitalWrite(PARACHUTE_PIN, HIGH);
    else
      digitalWrite(PARACHUTE_PIN, LOW);
    break;
  case 'W':
    Serial.write('W');
    Serial.write(value);
    if (value == 1)
      digitalWrite(WATERSPLASHER_PIN, HIGH);
    else
      digitalWrite(WATERSPLASHER_PIN, LOW);
    break;
  default:
    Serial.write('?');
    break;
  }
}

/** function to be fired at the zero crossing */
void zero_cross_detect() {
  numCrossing++;

  if (numCrossing > 10) {
    numCrossing = 0;
    numTenPack = (numTenPack + 1) % 12;
  }

  if (numTenPack == 11) {
    if (numCrossing < speedPercentage % 10)
      digitalWrite(FAN_PIN, HIGH);
    else
      digitalWrite(FAN_PIN, LOW);
  } else {
    if (numCrossing < speedPercentage / 10)
      digitalWrite(FAN_PIN, HIGH);
    else
      digitalWrite(FAN_PIN, LOW);
  }

  Serial.write(numCrossing);
}
