#!/usr/bin/python

import locale

import RPi.GPIO as GPIO

from flask import Flask, send_from_directory, jsonify
from flask.ext.socketio import SocketIO, emit

## Parameters
GPIO_FAN = 17
PWM_FREQUENCY = 1000


## REST API URLs
BASE_URL="/"
FAN_URL = BASE_URL + "fan/"


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
@app.route(FAN_URL + '<int:percent>', methods=['PUT'])
def set_fan_speed(percent):
	global duty_cycle

	# Set PWM-DutyCycle of pin
	led.ChangeDutyCycle(percent)
	duty_cycle = percent
	socketio.emit('fanEvent', {'data': 'Set fan speed to ' + str(percent)}, namespace="/events")

	return jsonify({'error': 0}), 200

@app.route(FAN_URL, methods=['GET'])
def get_fan_speed():
	return jsonify({'speed': duty_cycle}), 200


## Events
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
	duty_cycle = 0
	led.start(duty_cycle)

# Main - Start Flask server through SocketIO for websocket support
if __name__ == '__main__':
	# Set locale for Flask
	locale.setlocale(locale.LC_ALL, '')

	init_pwm()

	# Start Flask server
	app.debug = True
	socketio.run(app, host='0.0.0.0')

	# Reset GPIO
	led.stop()
	GPIO.cleanup()
