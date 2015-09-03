#!/usr/bin/python

#Initialize logger
import logging.config
logging.config.fileConfig('log.ini')

import sys
import locale
import struct
import threading
import time

try:
	import RPi.GPIO as GPIO
except Exception, e:
	logging.critical("Couldn't import RPi.GPIO. Exception: " + str(e))

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
JUMP_STATE_URL = BASE_URL + "jumpState/"


## Serial communication with Arduino
SERIAL_NAME = "/dev/ttyACM0"


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

@app.route(JUMP_STATE_URL, methods=['GET'])
def get_jump_state():
	return jsonify({'jumpStarted': jump_started}), 200

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
	logging.info("Got unity ready: " + str(message))
	emit('raspiUnityReadyEvent', {'data': message}, broadcast=True)

@socketio.on('unityJumpStartedEvent', namespace='/events')
def unity_ready(message):
	logging.info("Got jump started: " + str(message))
	trigger_start()
	emit('raspiJumpStartedEvent', {'data': message}, broadcast=True)

@socketio.on('unityParachuteOpenEvent', namespace='/events')
def unity_parachute(message):
	logging.info("Got open parachute: " + str(message))
	open_parachute()

@socketio.on('unityLandingEvent', namespace='/events')
def unity_landing(message):
	logging.info("Got landing: " + str(message))
	emit('raspiLandingEvent', {'data': message}, broadcast=True)

@socketio.on('unityResetLevel', namespace='/events')
def unity_reset(message):
	logging.info("Got Unity Reset: " + str(message))
	close_parachute()
	set_fanspeed(0)
	watersplasher_off()
	reset_start_trigger()

# Enivronment control
@socketio.on('unityFanSpeedEvent', namespace='/events')
def unity_fanspeed(message):
	logging.info("Got fanspeed: " + str(message))
	set_fanspeed(int(message))

@socketio.on('unityWaterSplasherOnEvent', namespace='/events')
def unity_watersplasher_on(message):
	logging.info("Got watersplasher-on: " + str(message))
	watersplasher_on()

@socketio.on('unityWaterSplasherOffEvent', namespace='/events')
def unity_watersplasher_off(message):
	logging.info("Got watersplasher-off: " + str(message))
	watersplasher_off()


## Raspberry GPIO
# Init
def init_gpio():
	global led
	global duty_cycle
	global parachute_state
	global watersplasher_state
	global jump_started

	try:
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

		# Setup output for water splasher
		GPIO.setup(GPIO_WATERSPLASHER, GPIO.OUT)
	except Exception, e:
		logging.error("Not able to initialize GPIO. Not on RPi? " + str(e))

	# Init state variables
	parachute_state = False;
	watersplasher_state = False;
	duty_cycle = 0
	jump_started = False

	try:
		# Init LED
		led = GPIO.PWM(GPIO_FAN, PWM_FREQUENCY)
		led.start(duty_cycle)

		# Init parachute and watersplasher
		GPIO.output(GPIO_PARACHUTE, GPIO.LOW)
		GPIO.output(GPIO_WATERSPLASHER, GPIO.LOW)
	except Exception, e:
		logging.error("Not able to apply initial state to GPIO. Not on RPi? " + str(e))


## Serial console
def init_serial():
	global serial_port
	global serial_lock

	try:
		# Init Serial port
		serial_port = serial.Serial(SERIAL_NAME, timeout=1)
		serial_port.flushInput()
		serial_port.flushOutput()
		serial_lock = threading.Lock()

		# Start logger thread
		log_thread = threading.Thread(target=log_port, args=(serial_port,))
		log_thread.start()
	except OSError, e:
		serial_port = None
		logging.error(str(e))
	except serial.serialutil.SerialException, e:
		serial_port = None
		logging.error(str(e))

	logging.debug("Serial: " + str(serial_port))

def send_serial_command(command, value):
	# Protocol: Start each message with 255 (= 0xFF)
	if value > 254 or value < 0:
		logging.error("Values allowed: 0 - 254!!! Not sending value " + str(value))
		return;

	message = int2bin(255) + command + int2bin(value)
	if (serial_port):
		serial_lock.acquire(True)
		ret = serial_port.write(message)
		logging.debug("Sent " + str(ret) + " Bytes: " + str(message) +
			" being " + str(command) + ", " + str(value))
		serial_lock.release()
	else:
		logging.error("Not sending - no serial port?")

def int2bin(value):
	return struct.pack('!B',value)

def bin2int(value):
	return struct.unpack('!B',value)[0]

def log_port(ser):
	global serial_lock

	if serial_port is not None:
		serial_port.flushInput()
	while serial_port is not None:
		reading = ser.read()
		if reading:
			logging.debug("Received bin: " + str(reading) + " int: " + str(bin2int(reading)))

	logging.info("Closing logger")


# Setter for fan speed
def set_fanspeed(speed):
	global duty_cycle

	logging.debug("Setting fanspeed to " + str(speed))

	# Set PWM-DutyCycle of pin
	duty_cycle = duty_cycle = min(max(speed, 0), 100)
	led.ChangeDutyCycle(int(duty_cycle))
	send_serial_command('F', duty_cycle)

	# TODO Remove when working
	socketio.emit('raspiFanEvent', speed, namespace="/events")

# Setter for parachute state
def open_parachute():
	global parachute_state

	logging.debug("Open parachute")

	GPIO.output(GPIO_PARACHUTE, GPIO.HIGH)
	send_serial_command('P', 1)
	parachute_state = True;
	socketio.emit('raspiParachuteOpenEvent', None, namespace="/events")

def close_parachute():
	global parachute_state

	logging.debug("Close parachute")

	GPIO.output(GPIO_PARACHUTE, GPIO.LOW)
	send_serial_command('P', 0)
	parachute_state = False;
	socketio.emit('raspiParachuteCloseEvent', None, namespace="/events")

# Setter for Watersplasher
def watersplasher_on():
	global watersplasher_state

	logging.debug("Watersplasher on")

	GPIO.output(GPIO_WATERSPLASHER, GPIO.HIGH)
	send_serial_command('W', 1)
	watersplasher_state = True;
	socketio.emit('raspiWaterSplasherOnEvent', None, namespace="/events")

def watersplasher_off():
	global watersplasher_state

	logging.debug("Watersplasher off")

	GPIO.output(GPIO_WATERSPLASHER, GPIO.LOW)
	send_serial_command('W', 0)
	watersplasher_state = False;
	socketio.emit('raspiWaterSplasherOffEvent', None, namespace="/events")

# Setter for start trigger
def trigger_start():
	global jump_started

	if not jump_started:
		send_serial_command('S', 1)
		jump_started = True

def reset_start_trigger():
	global jump_started

	send_serial_command('S', 0)
	jump_started = False


# RasPi GPIO button callbacks
def ready_button_event_handler(pin):
	socketio.emit('raspiPlayerReadyEvent', 'Player is ready to go', namespace="/events")

def start_button_event_handler(pin):
	socketio.emit('raspiStartJumpEvent', 'Jump Started', namespace="/events")
	socketio.emit('serverEvent', {'data': 'Jump Started'}, namespace="/events")


## Main - Start Flask server through SocketIO for websocket support
if __name__ == '__main__':
	global serial_port
	global start_time

	# Set locale for Flask
	#locale.setlocale(locale.LC_ALL, '')

	init_gpio()
	init_serial()

	# Set debug option if desired
	if "debug" in sys.argv:
		app.debug = True

	start_time = time.time()

	try:
		# Blocking! - Start Flask server
		socketio.run(app, host='0.0.0.0')
	except KeyboardInterrupt, e:
		pass

	# Close serial port
	logging.info("Close serial port")
	if serial_port is not None and serial_port.isOpen():
		serial_port.close()
		serial_port = None

	# Reset GPIO
	logging.info("Cleanup GPIO")

	try:
		led.stop()
		GPIO.cleanup()
	except Exception, e:
		logging.critical("Not able to clean up. " + str(e))
