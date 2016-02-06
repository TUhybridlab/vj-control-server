#!/usr/bin/python
import logging.config
import locale
import signal
import sys
import time

from flask import Flask, send_from_directory, jsonify, request
from flask.ext.socketio import SocketIO, emit

from vj_serial import SerialPort


## Initialize logger
logging.config.fileConfig('log.ini')


## See if GPIO is available
try:
	import RPi.GPIO as GPIO
	HIGH = GPIO.HIGH
	LOW = GPIO.LOW
except ImportError, error:
	GPIO = None
	HIGH = 'HIGH'
	LOW = 'LOW'
	logging.critical("Couldn't import RPi.GPIO. Exception: %s", error)


## Parameters
GPIO_FAN = 17
GPIO_PARACHUTE = 27
GPIO_WATERSPLASHER = 22

PWM_FREQUENCY = 1000

GPIO_BUTTON_START = 23
GPIO_BUTTON_READY = 24

## REST API URLs
BASE_URL = "/"
FAN_URL = BASE_URL + "fan/"
PARACHUTE_URL = BASE_URL + "parachute/"
WATERSPLASHER_URL = BASE_URL + "watersplasher/"
EVENT_URL = BASE_URL + "events/"
JUMP_STATE_URL = BASE_URL + "jumpState/"

## Serial communication with Arduino
SERIAL_NAME = "/dev/ttyACM0"


## Global variables
led = None
duty_cycle = 0
parachute_state = False
watersplasher_state = False
jump_started = False
start_time = None

serial = SerialPort(SERIAL_NAME)


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
	logging.info("Got unity ready: %s", message)
	emit('raspiUnityReadyEvent', {'data': message}, broadcast=True)

@socketio.on('unityJumpStartedEvent', namespace='/events')
def unity_jump_started(message):
	logging.info("Got jump started: %s", message)
	trigger_start()
	emit('raspiJumpStartedEvent', {'data': message}, broadcast=True)

@socketio.on('unityParachuteOpenEvent', namespace='/events')
def unity_parachute(message):
	logging.info("Got open parachute: %s", message)
	open_parachute()

@socketio.on('unityLandingEvent', namespace='/events')
def unity_landing(message):
	logging.info("Got landing: %s", message)
	emit('raspiLandingEvent', {'data': message}, broadcast=True)

@socketio.on('unityResetLevel', namespace='/events')
def unity_reset(message):
	logging.info("Got Unity Reset: %s", message)
	close_parachute()
	set_fanspeed(0)
	watersplasher_off()
	reset_start_trigger()

# Enivronment control
@socketio.on('unityFanSpeedEvent', namespace='/events')
def unity_fanspeed(message):
	logging.info("Got fanspeed: %s", message)
	set_fanspeed(int(message))

@socketio.on('unityWaterSplasherOnEvent', namespace='/events')
def unity_watersplasher_on(message):
	logging.info("Got watersplasher-on: %s", message)
	watersplasher_on()

@socketio.on('unityWaterSplasherOffEvent', namespace='/events')
def unity_watersplasher_off(message):
	logging.info("Got watersplasher-off: %s", message)
	watersplasher_off()


## Raspberry GPIO
# Init
def init_gpio():
	global led

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

		# Setup Fan debug LED
		led = GPIO.PWM(GPIO_FAN, PWM_FREQUENCY)
		led.start(duty_cycle)

		# Init parachute and watersplasher
		GPIO.output(GPIO_PARACHUTE, LOW)
		GPIO.output(GPIO_WATERSPLASHER, LOW)
	except AttributeError, error:
		logging.error("Not able to apply initial state to GPIO. Not on RPi? Reason: %s", error)

def set_gpio(pin, value):
	if GPIO:
		GPIO.output(pin, value)
	else:
		logging.error('Cannot set pin %i to %s!', pin, value)


## Helpers
# Setter for fan speed
def set_fanspeed(speed):
	logging.debug("Setting fanspeed to %s", speed)

	# Set PWM-DutyCycle of pin
	duty_cycle = duty_cycle = min(max(speed, 0), 100)
	serial.send_serial_command('F', duty_cycle)

	# TODO Remove when working
	socketio.emit('raspiFanEvent', speed, namespace="/events")

	if led:
		led.ChangeDutyCycle(int(duty_cycle))
	else:
		logging.critical("No LED!")

# Setter for parachute state
def open_parachute():
	logging.debug("Open parachute")

	set_gpio(GPIO_PARACHUTE, HIGH)
	serial.send_serial_command('P', 1)
	parachute_state = True
	socketio.emit('raspiParachuteOpenEvent', None, namespace="/events")

def close_parachute():
	logging.debug("Close parachute")

	set_gpio(GPIO_PARACHUTE, LOW)
	serial.send_serial_command('P', 0)
	parachute_state = False
	socketio.emit('raspiParachuteCloseEvent', None, namespace="/events")

# Setter for Watersplasher
def watersplasher_on():
	logging.debug("Watersplasher on")

	set_gpio(GPIO_WATERSPLASHER, HIGH)
	serial.send_serial_command('W', 1)
	watersplasher_state = True
	socketio.emit('raspiWaterSplasherOnEvent', None, namespace="/events")

def watersplasher_off():
	logging.debug("Watersplasher off")

	set_gpio(GPIO_WATERSPLASHER, LOW)
	serial.send_serial_command('W', 0)
	watersplasher_state = False
	socketio.emit('raspiWaterSplasherOffEvent', None, namespace="/events")

# Setter for start trigger
def trigger_start():
	if not jump_started:
		serial.send_serial_command('S', 1)
		jump_started = True

def reset_start_trigger():
	serial.send_serial_command('S', 0)
	jump_started = False


# RasPi GPIO button callbacks
def ready_button_event_handler(pin):
	socketio.emit('raspiPlayerReadyEvent', 'Player is ready to go', namespace="/events")

def start_button_event_handler(pin):
	socketio.emit('raspiStartJumpEvent', 'Jump Started', namespace="/events")
	socketio.emit('serverEvent', {'data': 'Jump Started'}, namespace="/events")


## Shutdown signal handler
def sigTermHandler(signum, frame):
	raise KeyboardInterrupt('Signal %i receivied!' % signum)


## Main - Start Flask server through SocketIO for websocket support
def main():
	# Set locale for Flask
	#locale.setlocale(locale.LC_ALL, '')

	init_gpio()

	# Set debug option if desired
	if "debug" in sys.argv:
		app.debug = True

	start_time = time.time()

	try:
		# Set signal handler for Shutdown
		signal.signal(signal.SIGTERM, sigTermHandler)

		# Blocking! - Start Flask server
		socketio.run(app, host='0.0.0.0')
	except KeyboardInterrupt:
		pass
	finally:
		serial.close()

		# Reset GPIO
		logging.info("Cleanup GPIO")
		try:
			led.stop()
			GPIO.cleanup()
		except AttributeError, error:
			logging.exception("Not able to clean up. Reason: %s", error)

if __name__ == '__main__':
	main()
