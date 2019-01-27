import time
from RPi import GPIO

from common import pattern


class PushSwitch(pattern.EventEmitter, pattern.Logger):
  """Class for any switch that can be pressed.

  Events:
    "push": triggered when switch is pushed and released.
  """

  _IGNORE_THRESHOLD = 0.25

  def __init__(self, name, pin, *args, **kwargs):
    super(PushSwitch, self).__init__(self, *args, **kwargs)
    self._name = name
    self._last_press = time.time()
    if pin:
      GPIO.setmode(GPIO.BCM)
      GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
      GPIO.add_event_detect(pin, GPIO.FALLING, callback=self._on_pressed)

  def _on_pressed(self, channel):
    interval = time.time() - self._last_press
    if interval > self._IGNORE_THRESHOLD:
      self.logger.info('[{0}] pressed (interval={1})'.format(self._name, interval))
      self.emit('push')
    self._last_press = time.time()