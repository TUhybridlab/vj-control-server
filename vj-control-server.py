#!/usr/bin/python

import locale

import RPi.GPIO as GPIO

from flask import Flask, send_from_directory

## Parameters
GPIO_FAN = 17
PWM_FREQUENCY = 1000


## Flask
BASE_URL="/"
FAN_URL = BASE_URL + "fan/"
app = Flask(__name__)


## Deliver index.html, css and js files
@app.route(BASE_URL)
def index():
	return send_from_directory('static', 'index.html')

@app.route(BASE_URL + 'css/<path:path>')
def static_css_proxy(path):
	return send_from_directory('static/css/', path)

@app.route(BASE_URL + 'js/<path:path>')
def static_js_proxy(path):
	return send_from_directory('static/js/', path)

@app.route(BASE_URL + 'images/<path:path>')
def static_img_proxy(path):
	return send_from_directory('static/images/', path)

## REST API
@app.route(FAN_URL + '<int:percent>', methods=['PUT'])
def set_fan_speed(percent):
	global duty_cycle

	# Set servo on GPIO17 to 1000micros (1.0ms)
	led.ChangeDutyCycle(percent)
	duty_cycle = percent
	return jsonify({'error': 0}), 200

@app.route(FAN_URL, methods=['GET'])
def get_fan_speed():
	# Set servo on GPIO17 to 1000micros (1.0ms)
	return jsonify({'speed': duty_cycle}), 200


## Init Raspberry GPIO
def init_led():
	global led
	global duty_cycle

	# Setup PWM for fan control
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(GPIO_FAN, GPIO.OUT)
	led = GPIO.PWM(GPIO_FAN, PWM_FREQUENCY)
	duty_cycle = 0
	led.start(duty_cycle)

# Main - Start Flask server
if __name__ == '__main__':
	# Set locale for Flask
	locale.setlocale(locale.LC_ALL, '')

	init_led()

	# Start Flask server
	app.run(host='0.0.0.0')

	# Reset GPIO
	led.stop()
	GPIO.cleanup()
