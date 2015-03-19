#!/usr/bin/python

import sys
import locale

import RPi.GPIO as GPIO

from flask import Flask, send_from_directory, jsonify, request
from flask.ext.socketio import SocketIO, emit


## Parameters
GPIO_FAN = 17
GPIO_PARACHUTE = 22
GPIO_WATERSPLASHER = 24

PWM_FREQUENCY = 1000

GPIO_BUTTON_START = 23
GPIO_BUTTON_READY = 24

## REST API URLs
BASE_URL="/"
FAN_URL = BASE_URL + "fan/"
EVENT_URL = BASE_URL + "events/"


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

@app.route(EVENT_URL, methods=['POST'])
def broadcast_event():
	if request.json and 'data' in request.json:
		socketio.emit('serverEvent', {'data': request.json['data']}, namespace="/events")
	else:
		socketio.emit('serverEvent', {'data': request.form['data']}, namespace="/events")

	return jsonify({'error': 0}), 201


## Events

@socketio.on('unityReadyEvent', namespace='/events')
def unity_ready(message):
	emit('serverEvent', {'data': message}, broadcast=True)

@socketio.on('unityParachuteEvent', namespace='/events')
def unity_parachute(message):
	GPIO.output(GPIO_PARACHUTE, True)
	emit('serverEvent', {'data': message}, broadcast=True)

@socketio.on('unityLandingEvent', namespace='/events')
def unity_landing(message):
	emit('serverEvent', {'data': message}, broadcast=True)

@socketio.on('unityFanSpeedEvent', namespace='/events')
def unity_fanspeed(message):
	set_fanspeed(int(message))

@socketio.on('unityWaterSplasherOnEvent', namespace='/events')
def unity_watersplasher_on(message):
	GPIO.output(GPIO_WATERSPLASHER, True)
	emit('serverEvent', {'data': message}, broadcast=True)

@socketio.on('unityWaterSplasherOnEvent', namespace='/events')
def unity_watersplasher_off(message):
	GPIO.output(GPIO_WATERSPLASHER, False)
	emit('serverEvent', {'data': message}, broadcast=True)


## RasPi GPIO callbacks
def ready_button_event_handler(pin):
	socketio.emit('raspiPlayerReadyEvent', 'Player is ready to go', namespace="/events")

def start_button_event_handler(pin):
	socketio.emit('raspiStartJumpEvent', 'Jump Started', namespace="/events")
	socketio.emit('serverEvent', {'data': 'Jump Started'}, namespace="/events")


## Init Raspberry GPIO
def init_pwm():
	global led
	global duty_cycle

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

    # Init LED
	led = GPIO.PWM(GPIO_FAN, PWM_FREQUENCY)
	duty_cycle = 50
	led.start(duty_cycle)

	# Init parachute and watersplasher
	GPIO.output(GPIO_PARACHUTE, False)
	GPIO.output(GPIO_WATERSPLASHER, False)

## Setter for fan speed
def set_fanspeed(speed):
	global duty_cycle

	# Set PWM-DutyCycle of pin
	duty_cycle = duty_cycle = min(max(speed, 0), 100)
	led.ChangeDutyCycle(int(duty_cycle))

	# TODO Remove when working
	socketio.emit('serverEvent', {'data': 'Set fan speed to ' + str(duty_cycle)}, namespace="/events")


# Main - Start Flask server through SocketIO for websocket support
if __name__ == '__main__':
	# Set locale for Flask
	locale.setlocale(locale.LC_ALL, '')

	init_pwm()

	# Set debug option if desired
	if "debug" in sys.argv:
		app.debug = True

	# Blocking! - Start Flask server
	socketio.run(app, host='0.0.0.0')

	# Reset GPIO
	led.stop()
	GPIO.cleanup()
