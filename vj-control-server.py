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

## Init Raspberry GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_FAN, GPIO.OUT)
led = GPIO.PWM(GPIO_FAN, PWM_FREQUENCY)

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
	# Set servo on GPIO17 to 1000micros (1.0ms)
	led.ChangeDutyCycle(percent)
	return jsonify({'error': 0}), 200

def init_led():
	# Setup PWM for fan control
	led.start(0)

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
