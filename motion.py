import threading
import time

from RPi import GPIO
from common import pattern


class PIRMotionSensor(pattern.EventEmitter, pattern.Closable, pattern.Logger,
                      pattern.Startable, pattern.Stopable):

  _NO_MOTION_DELAY = 8  # sec

  def __init__(self, pin=18, *args, **kwargs):
    super(PIRMotionSensor, self).__init__(self, *args, **kwargs)

    self._pin = pin
    self._in_motion = False
    self._timer = None

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self._pin, GPIO.IN)

  @property
  def in_motion(self):
    return self._in_motion

  def start(self):
    GPIO.add_event_detect(self._pin, GPIO.BOTH, callback=self._triggered)

  def stop(self):
    GPIO.remove_event_detect(self._pin)
    GPIO.cleanup()

  def close(self):
    self.stop()

  def _triggered(self, pin):
    has_motion = GPIO.input(pin)
    self.logger.debug('Motion: {0}'.format(has_motion))

    if self._timer:
      self._timer.cancel()
      self._timer = None

    if has_motion:
      self._motion_started()
    else:
      self._timer = threading.Timer(self._NO_MOTION_DELAY,
                                    self._motion_stopped)
      self._timer.start()

  def _motion_started(self):
    if not self._in_motion:
      self._in_motion = True
      self.emit('motion start')

  def _motion_stopped(self):
    if self._in_motion:
      self._in_motion = False
      self.emit('motion stop')
