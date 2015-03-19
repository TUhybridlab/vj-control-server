#!/usr/bin/python

import sys
import locale

import RPi.GPIO as GPIO

from flask import Flask, send_from_directory, jsonify, request
from flask.ext.socketio import SocketIO, emit


## Parameters
GPIO_FAN = 17
PWM_FREQUENCY = 1000


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
## DEPRECATED - Events are broadcasted as they come in on POST requests
@socketio.on('webEvent', namespace='/events')
def test_message(message):
	emit('serverEvent', {'data': message['data']}, broadcast=True)


## Init Raspberry GPIO
def init_pwm():
	global led
	global duty_cycle

	# Setup PWM for fan control
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(GPIO_FAN, GPIO.OUT)
	led = GPIO.PWM(GPIO_FAN, PWM_FREQUENCY)
	duty_cycle = 50
	led.start(duty_cycle)

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
