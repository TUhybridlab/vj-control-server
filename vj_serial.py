import logging
import struct
import threading

import serial
import serial.tools.list_ports

COMMAND_TO_CHANNEL = {
	'F': 0x00,
	'W': 0x01,
	'H': 0x02,
	'C': 0x03
}


class SerialPort(object):
	def __init__(self, port_name):
		self.port_name = port_name
		self.serial_port = None
		self.serial_lock = None
		self.log_thread = None

		self.serial_lock = threading.Lock()
		self.initSerialPort()

	def initSerialPort(self):
		port_device = self.get_serial_port_device()
		logging.info("Initializing port %s", port_device)
		try:
			# Init Serial port
			self.serial_port = serial.Serial(port_device, timeout=1, baudrate=115200)
			self.serial_port.flushInput()
			self.serial_port.flushOutput()

		except (OSError, serial.serialutil.SerialException) as error:
			logging.error("Cannot initialize. Reason: %s", error)
			from vjdummyserial import VjDummySerial
			self.serial_port = VjDummySerial(port_device)
			logging.error("Running on dummy serial")

		logging.debug("Serial: %s", self.serial_port)

	def _send_serial_command(self, command, value):
		if command not in COMMAND_TO_CHANNEL:
			logging.error("Unknown command: %s", command)
			return

		message = self.int2bin(0xF6) + self.int2bin(0x6F) + self.int2bin(0x04) + self.int2bin(COMMAND_TO_CHANNEL[command]) + self.int2bin(value)

		if self.serial_port:
			try:
				self.serial_lock.acquire(True)
				ret = self.serial_port.write(message)
				logging.debug("Sent %s Bytes, being", ret)
				for x in message:
					logging.debug("%s", self.bin2int(x))
			finally:
				self.serial_lock.release()
		else:
			logging.error("Not sending %s, %s - no serial port?", command, value)

	def send_serial_command(self, command, value):
		if not self.serial_port:
			self.initSerialPort()

		if self.serial_port:
			try:
				self._send_serial_command(command, value)
			except IOError:
				self.initSerialPort()
				self._send_serial_command(command, value)

	def get_serial_port_device(self):
		ports = serial.tools.list_ports.grep(self.port_name)
		try:
			return next(ports).device
		except StopIteration:
			return None

	@staticmethod
	def int2bin(value):
		return struct.pack('!B', value)

	@staticmethod
	def bin2int(value):
		if isinstance(value, int):
			return value
		return struct.unpack('!B', value)[0]

	def close(self):
		# Close serial port
		logging.info("Close serial port")
		if self.serial_port is not None and self.serial_port.isOpen():
			self.serial_port.close()
			self.serial_port = None
