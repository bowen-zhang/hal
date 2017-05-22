import time

from RPi import GPIO

from common import pattern


class RelaySwitch(pattern.Logger):

  def __init__(self, pin, *args, **kwargs):
    super(RelaySwitch, self).__init__(*args, **kwargs)

    self._pin = pin
    self.logger.info('Initializing pin {0}'.format(self._pin))
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self._pin, GPIO.OUT)
    GPIO.output(self._pin, GPIO.HIGH)

  def toggle(self):
    self.logger.info('Toggling relay...')
    GPIO.output(self._pin, GPIO.LOW)
    time.sleep(0.3)
    GPIO.output(self._pin, GPIO.HIGH)

  def off(self):
    self.logger.info('Turning off relay...')
    GPIO.output(self._pin, GPIO.LOW)

  def on(self):
    self.logger.info('Turning on relay...')
    GPIO.output(self._pin, GPIO.HIGH)
