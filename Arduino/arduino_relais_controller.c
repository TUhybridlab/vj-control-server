// set pin numbers:

//output 1,5,3,4
int lampe [] = {9, 10, 8, 11, 7, 12, 6, 13, 22, 21, 24, 20, 26, 19, 28, 18, 32, 30, 36, 34, 40, 38, 44, 42, 33, 31, 37, 35, 41, 39, 45, 43};

int FAN_PIN = lampe[0];
int PARACHUTE_PIN = lampe[1];
int WATERSPLASHER_PIN = lampe[2];


void setup() {
	Serial.begin(115200);

	pinMode(FAN_PIN, OUTPUT);
	pinMode(PARACHUTE_PIN, OUTPUT);
	pinMode(WATERSPLASHER_PIN, OUTPUT);
}

void loop()
{
	char messsage[] = NULL;

	char command = 0;
	char value = 0;

	if(Serial.available() > 0) {
		message = Serial.readln();

		command = message[0];
		value = message[1];

		switch(command) {
			case 'F':
				analogWrite(FAN_PIN, value);
				break;
			case 'P':
				if (value == 1)
					digitalWrite(PARACHUTE_PIN, HIGH);
				else
					digitalWrite(PARACHUTE_PIN, LOW);
				break;
			case 'W':
				if (value == 1)
					digitalWrite(WATERSPLASHER_PIN, HIGH);
				else
					digitalWrite(WATERSPLASHER_PIN, LOW);
				break;
			default:
				break;
		}
	}
}
