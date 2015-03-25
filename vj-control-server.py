#!/usr/bin/python

import sys
import locale

import RPi.GPIO as GPIO

import serial

from flask import Flask, send_from_directory, jsonify, request
from flask.ext.socketio import SocketIO, emit


## Parameters
GPIO_FAN = 17
GPIO_PARACHUTE = 27
GPIO_WATERSPLASHER = 22

PWM_FREQUENCY = 1000

GPIO_BUTTON_START = 23
GPIO_BUTTON_READY = 24

## REST API URLs
BASE_URL="/"
FAN_URL = BASE_URL + "fan/"
PARACHUTE_URL = BASE_URL + "parachute/"
WATERSPLASHER_URL = BASE_URL + "watersplasher/"
EVENT_URL = BASE_URL + "events/"


# TODO: Hook Up Arduino's serial
## Serial communication with Arduino
SERIAL_NAME = "/dev/ttyUSB0"


## Instanciate Flask (Static files and REST API)
app = Flask(__name__)
## Instanciate SocketIO (Websockets, used for events) on top of it
socketio = SocketIO(app)


## Deliver statc files (index.html, css, images and js files)
@app.route(BASE_URL)
def index():
	return send_from_directory('static', 'index.html')

@app.route(BASE_URL + 'css/<path:path>')
def static_css_proxy(path):
	return send_from_directory('static/css/', path)

@app.route(BASE_URL + 'js/<path:path>')
def static_js_proxy(path):
	return send_from_directory('static/js/', path)


## REST API
@app.route(FAN_URL + '<int:speed>', methods=['PUT', 'GET'])
def set_fan_speed(speed):
	set_fanspeed(speed)

	return jsonify({'error': 0}), 200

@app.route(FAN_URL, methods=['POST'])
def set_fan_speed_post():
	set_fanspeed(request.form['speed'])

	return jsonify({'error': 0}), 200

@app.route(FAN_URL, methods=['GET'])
def get_fan_speed():
	return jsonify({'speed': duty_cycle}), 200

@app.route(PARACHUTE_URL, methods=['GET'])
def get_parachute_state():
	return jsonify({'parachute': parachute_state}), 200

@app.route(WATERSPLASHER_URL, methods=['GET'])
def get_watersplasher_state():
	return jsonify({'watersplasher': watersplasher_state}), 200

@app.route(EVENT_URL, methods=['POST'])
def broadcast_event():
	if request.json and 'data' in request.json:
		socketio.emit('serverEvent', {'data': request.json['data']}, namespace="/events")
	else:
		socketio.emit('serverEvent', {'data': request.form['data']}, namespace="/events")

	return jsonify({'error': 0}), 201


## Events
# Section of the Jump
@socketio.on('unityReadyEvent', namespace='/events')
def unity_ready(message):
	emit('raspiUnityReadyEvent', {'data': message}, broadcast=True)

@socketio.on('unityJumpStartedEvent', namespace='/events')
def unity_ready(message):
	emit('raspiJumpStartedEvent', {'data': message}, broadcast=True)

@socketio.on('unityParachuteOpenEvent', namespace='/events')
def unity_parachute(message):
	open_parachute()

@socketio.on('unityLandingEvent', namespace='/events')
def unity_landing(message):
	emit('raspiLandingEvent', {'data': message}, broadcast=True)

@socketio.on('unityResetLevel', namespace='/events')
def unity_reset(message):
	close_parachute()
	set_fanspeed(0)
	watersplasher_off()

# Enivronment control
@socketio.on('unityFanSpeedEvent', namespace='/events')
def unity_fanspeed(message):
	set_fanspeed(int(message))

@socketio.on('unityWaterSplasherOnEvent', namespace='/events')
def unity_watersplasher_on(message):
	watersplasher_on()

@socketio.on('unityWaterSplasherOffEvent', namespace='/events')
def unity_watersplasher_off(message):
	watersplasher_off()


## Raspberry GPIO
# Init
def init_gpio():
	global led
	global duty_cycle
	global parachute_state
	global watersplasher_state

	GPIO.setmode(GPIO.BCM)

	# Setup PWM for fan control
	GPIO.setup(GPIO_FAN, GPIO.OUT)

	# Setup button for start detection
	GPIO.setup(GPIO_BUTTON_START, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.add_event_detect(GPIO_BUTTON_START, GPIO.FALLING)
	GPIO.add_event_callback(GPIO_BUTTON_START, start_button_event_handler)

	# Setup button for ready-state detection
	GPIO.setup(GPIO_BUTTON_READY, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.add_event_detect(GPIO_BUTTON_READY, GPIO.FALLING)
	GPIO.add_event_callback(GPIO_BUTTON_READY, ready_button_event_handler)

	# Setup output for parachute
	GPIO.setup(GPIO_PARACHUTE, GPIO.OUT)
	parachute_state = False;

	# Setup output for water splasher
	GPIO.setup(GPIO_WATERSPLASHER, GPIO.OUT)
	watersplasher_state = False;

    # Init LED
	led = GPIO.PWM(GPIO_FAN, PWM_FREQUENCY)
	duty_cycle = 0
	led.start(duty_cycle)

	# Init parachute and watersplasher
	GPIO.output(GPIO_PARACHUTE, GPIO.LOW)
	GPIO.output(GPIO_WATERSPLASHER, GPIO.LOW)


## Serial console
def init_serial():
	global serialPort

	try:
		serialPort = serial.Serial(SERIAL_NAME)
	except OSError:
		serialPort = None

def send_serial_command(command, value):
	if (serialPort):
		ret = serialPort.write("" + command + int2bin(value))

	print "Sent", ret, "Bytes"

def int2bin(value):
	return struct.pack('!B',value)


# Setter for fan speed
def set_fanspeed(speed):
	global duty_cycle

	# Set PWM-DutyCycle of pin
	duty_cycle = duty_cycle = min(max(speed, 0), 100)
	led.ChangeDutyCycle(int(duty_cycle))
	send_serial_command('F', duty_cycle)

	# TODO Remove when working
	socketio.emit('raspiFanEvent', speed, namespace="/events")

# Setter for parachute state
def open_parachute():
	global parachute_state

	GPIO.output(GPIO_PARACHUTE, GPIO.HIGH)
	send_serial_command('P', 1)
	parachute_state = True;
	socketio.emit('raspiParachuteOpenEvent', None, namespace="/events")

def close_parachute():
	global parachute_state

	GPIO.output(GPIO_PARACHUTE, GPIO.LOW)
	send_serial_command('P', 0)
	parachute_state = False;
	socketio.emit('raspiParachuteCloseEvent', None, namespace="/events")

# Setter for Watersplasher
def watersplasher_on():
	global watersplasher_state

	GPIO.output(GPIO_WATERSPLASHER, GPIO.HIGH)
	send_serial_command('W', 1)
	watersplasher_state = True;
	socketio.emit('raspiWaterSplasherOnEvent', None, namespace="/events")

def watersplasher_off():
	global watersplasher_state

	GPIO.output(GPIO_WATERSPLASHER, GPIO.LOW)
	send_serial_command('W', 0)
	watersplasher_state = False;
	socketio.emit('raspiWaterSplasherOffEvent', None, namespace="/events")

# RasPi GPIO button callbacks
def ready_button_event_handler(pin):
	socketio.emit('raspiPlayerReadyEvent', 'Player is ready to go', namespace="/events")

def start_button_event_handler(pin):
	socketio.emit('raspiStartJumpEvent', 'Jump Started', namespace="/events")
	socketio.emit('serverEvent', {'data': 'Jump Started'}, namespace="/events")


## Main - Start Flask server through SocketIO for websocket support
if __name__ == '__main__':
	# Set locale for Flask
	locale.setlocale(locale.LC_ALL, '')

	init_gpio()
	init_serial()

	# Set debug option if desired
	if "debug" in sys.argv:
		app.debug = True

	try:
		# Blocking! - Start Flask server
		socketio.run(app, host='0.0.0.0')
	except KeyboardInterrupt, e:
		pass

	# Reset GPIO
	print "Cleanup GPIO"
	led.stop()
	GPIO.cleanup()
