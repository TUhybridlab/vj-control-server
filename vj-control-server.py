#!/usr/bin/python
import logging.config
import locale
import signal
import sys
import time

from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit
from recordclass import recordclass

from vj_serial import SerialPort


## Parameters
GPIO_FAN = 17
GPIO_PARACHUTE = 27
GPIO_WATERSPLASHER = 22

PWM_FREQUENCY = 1000

GPIO_BUTTON_START = 23
GPIO_BUTTON_READY = 24

MAX_WATERSPLASHER_DURATION = 10

## REST API URLs
BASE_URL = "/"
FAN_URL = BASE_URL + "fan/"
PARACHUTE_URL = BASE_URL + "parachute/"
WATERSPLASHER_URL = BASE_URL + "watersplasher/"
EVENT_URL = BASE_URL + "events/"
JUMP_STATE_URL = BASE_URL + "jumpState/"

## Serial communication with Arduino
SERIAL_NAME = "/dev/ttyUSB"


EnvState = recordclass(
	'EnvState', ['duty_cycle', 'parachute_state', 'watersplasher_state'])
JumpState = recordclass(
	'JumpState', ['jump_started', 'start_time'])


## Global variables
envState = EnvState(0, False, False)
jumpState = JumpState(False, None)
serial = None
activeWaterStopThread = 0


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
	return jsonify({'speed': envState.duty_cycle}), 200

@app.route(PARACHUTE_URL, methods=['GET'])
def get_parachute_state():
	return jsonify({'parachute': envState.parachute_state}), 200

@app.route(WATERSPLASHER_URL, methods=['GET'])
def get_watersplasher_state():
	return jsonify({'watersplasher': envState.watersplasher_state}), 200

@app.route(JUMP_STATE_URL, methods=['GET'])
def get_jump_state():
	return jsonify({'jumpStarted': jumpState.jump_started}), 200

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

@socketio.on('unityWaterSplasherEvent', namespace='/events')
def unity_watersplasher(message):
	logging.info("Got watersplasher: %s", message)
	if (int(message) == 1):
		watersplasher_on()
	else:
		watersplasher_off()


## Helpers
# Setter for fan speed
def set_fanspeed(speed):
	logging.debug("Setting fanspeed to %s", speed)

	# Set PWM-DutyCycle of pin
	envState.duty_cycle = min(max(speed, 0), 16)
	serial.send_serial_command('F', envState.duty_cycle)

	# TODO Remove when working
	socketio.emit('raspiFanEvent', speed, namespace="/events")

# Setter for parachute state
def open_parachute():
	logging.debug("Open parachute")

	serial.send_serial_command('P', 1)
	envState.parachute_state = True
	socketio.emit('raspiParachuteOpenEvent', None, namespace="/events")

def close_parachute():
	logging.debug("Close parachute")

	serial.send_serial_command('P', 0)
	envState.parachute_state = False
	socketio.emit('raspiParachuteCloseEvent', None, namespace="/events")

# Setter for Watersplasher
def stop_watersplasher_task(threadId, duration=MAX_WATERSPLASHER_DURATION):
	global activeWaterStopThread

	socketio.sleep(duration)
	if activeWaterStopThread == threadId:
		watersplasher_off()
		activeWaterStopThread = 0
	else:
		logging.info("Not closing, active one is %s", activeWaterStopThread)

def watersplasher_on():
	global activeWaterStopThread

	logging.debug("Watersplasher on")

	serial.send_serial_command('W', 16)
	envState.watersplasher_state = True

	activeWaterStopThread += 1
	socketio.start_background_task(stop_watersplasher_task, activeWaterStopThread)
	logging.info("Starting stopper thread: %s", activeWaterStopThread)

	socketio.emit('raspiWaterSplasherOnEvent', None, namespace="/events")

def watersplasher_off():
	logging.debug("Watersplasher off")

	serial.send_serial_command('W', 0)
	envState.watersplasher_state = False
	socketio.emit('raspiWaterSplasherOffEvent', None, namespace="/events")

# Setter for start trigger
def trigger_start():
	if not jumpState.jump_started:
		serial.send_serial_command('S', 1)
		jumpState.jump_started = True

def reset_start_trigger():
	serial.send_serial_command('S', 0)
	jumpState.jump_started = False


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
	global serial

	# Set locale for Flask
	#locale.setlocale(locale.LC_ALL, '')

	## Initialize logger
	logging.config.fileConfig('log.ini')

	# Init serial port
	serial = SerialPort(SERIAL_NAME)

	# Set debug option if desired
	if "debug" in sys.argv:
		app.debug = True

	jumpState.start_time = time.time()

	try:
		# Set signal handler for Shutdown
		signal.signal(signal.SIGTERM, sigTermHandler)

		# Blocking! - Start Flask server
		socketio.run(app, host='0.0.0.0')
	except KeyboardInterrupt:
		pass
	finally:
		serial.close()

if __name__ == '__main__':
	main()
