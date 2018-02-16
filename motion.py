from RPi import GPIO
from common import pattern


class PIRMotionSensor(pattern.EventEmitter, pattern.Closable):

  def __init__(self, pin=18, *args, **kwargs):
    super(PIRMotionSensor, self).__init__(self, *args, **kwargs)
    self._pin = pin
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self._pin, GPIO.IN)

  def _motion(self, pin):
    has_motion = GPIO.input(pin)
    if has_motion:
      self.emit('detected')
    self.emit('motion', has_motion)

  def start(self):
    GPIO.add_event_detect(self._pin, GPIO.BOTH, callback=self._motion)

  def stop(self):
    GPIO.remove_event_detect(self._pin)
    GPIO.cleanup()

  def close(self):
    self.stop()
