// set pin numbers:

//output 1,5,3,4
//int lampe [] = {
//  9, 10, 8, 11, 7, 12, 6, 13, 22, 21, 24, 20, 26, 19, 28, 18, 32, 30, 36, 34, 40, 38, 44, 42, 33, 31, 37, 35, 41, 39, 45, 43};

static const int FAN_PIN = 9;
static const int PARACHUTE_PIN = 10;
static const int WATERSPLASHER_PIN = 8;
static const int ZERO_CROSSING_INTERRUPT = 1;

volatile int numCrossing = 0;
volatile int speedPercentage = 0;

void setup() {
  Serial.begin(9600);

  pinMode(FAN_PIN, OUTPUT);
  pinMode(PARACHUTE_PIN, OUTPUT);
  pinMode(WATERSPLASHER_PIN, OUTPUT);

  attachInterrupt(ZERO_CROSSING_INTERRUPT, zero_cross_detect, RISING);
}

void loop()
{
  int command = 0;
  int value = 0;

  while(Serial.available() < 1){
    ;
  }
  command = Serial.read();
  while(Serial.available() < 1){
    ;
  }   
  value = Serial.read();

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
    Serial.write('d');
    break;
  }
}

/** function to be fired at the zero crossing */
void zero_cross_detect() {
  numCrossing = (numCrossing + 1) % 100;
  
  if (numCrossing < speedPercentage)
    digitalWrite(FAN_PIN, HIGH);
  else
    digitalWrite(FAN_PIN, LOW);
  
  Serial.write(numCrossing);
}

