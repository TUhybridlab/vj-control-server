import dummyserial


class VjDummySerial(dummyserial.Serial):
	def __init__(self, port):
		super(VjDummySerial, self).__init__(port=port)

	def isOpen(self):
		return self._isOpen
