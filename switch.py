from RPi import GPIO

from common import pattern


class TactileSwitch(pattern.EventEmitter, pattern.Logger):
  """Class for tactile switch.

  Events:
    "push": triggered when switch is pushed and released.
  """

  def __init__(self, name, pin, *args, **kwargs):
    super(TactileSwitch, self).__init__(self, *args, **kwargs)
    self._name = name
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(pin, GPIO.FALLING, callback=self._on_pressed)

  def _on_pressed(self, channel):
    self.logger.info('[{0}] pressed'.format(self._name))
    self.emit('push')