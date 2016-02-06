import logging
import struct
import threading

import serial


class SerialPort(object):
	def __init__(self, port_name):
		self.serial_port = None
		self.serial_lock = None
		self.log_thread = None

		try:
			# Init Serial port
			self.serial_port = serial.Serial(port_name, timeout=1)
			self.serial_port.flushInput()
			self.serial_port.flushOutput()
			self.serial_lock = threading.Lock()

			# Start logger thread
			self.log_thread = threading.Thread(target=self.log_port, args=(self.serial_port,))
			self.log_thread.start()
		except OSError, error:
			self.serial_port = None
			logging.error("Cannot initialize. Reason: %s", error)
		except serial.serialutil.SerialException, error:
			self.serial_port = None
			logging.error("Cannot initialize. Reason: %s", error)

		logging.debug("Serial: %s", self.serial_port)

	def send_serial_command(self, command, value):
		# Protocol: Start each message with 255 (= 0xFF)
		if value > 254 or value < 0:
			logging.error("Values allowed: 0 - 254!!! Not sending value %s", value)
			return

		message = self.int2bin(255) + command + self.int2bin(value)
		if self.serial_port:
			try:
				self.serial_lock.acquire(True)
				ret = self.serial_port.write(message)
				logging.debug("Sent %s Bytes: %s being %s , %s", ret, message, command, value)
			finally:
				self.serial_lock.release()
		else:
			logging.error("Not sending %s, %s - no serial port?", command, value)

	@staticmethod
	def int2bin(value):
		return struct.pack('!B', value)

	@staticmethod
	def bin2int(value):
		return struct.unpack('!B', value)[0]

	def log_port(self, ser):
		if self.serial_port is not None:
			self.serial_port.flushInput()
		while self.serial_port is not None:
			reading = ser.read()
			if reading:
				logging.debug("Received: %s, int: %s", reading, self.bin2int(reading))

		logging.info("Closing logger")

	def close(self):
		# Close serial port
		logging.info("Close serial port")
		if self.serial_port is not None and self.serial_port.isOpen():
			self.serial_port.close()
			self.serial_port = None
