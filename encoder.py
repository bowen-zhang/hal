from RPi import GPIO

from common import pattern


class Direction(object):
  CLOCKWISE = 1
  COUNTERCLOCKWISE = -1


class RotaryEncoder(pattern.EventEmitter, pattern.Logger):
  """Class for pushable single rotary encoder.

  Events:
    "rotate": triggered when rotary encoder is rotated.
      direction (Direction)
      value (int)
    "clockwise": triggered when rotary encoder is rotated clockwise for one step.
    "counterclockwise": triggered when rotary encoder is rotated counter clockwise for one step.
    "push": triggered when rotary encoder is pushed.
  """

  def __init__(self, name, clk_pin, dt_pin, sw_pin, *args, **kwargs):
    super(RotaryEncoder, self).__init__(*args, **kwargs)
    self._name = name
    self._counter = 0
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(clk_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(dt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    self._clk_last_state = GPIO.input(clk_pin)
    self._dt_last_state = GPIO.input(dt_pin)
    GPIO.add_event_detect(clk_pin, GPIO.BOTH, callback=self._clk_callback)
    GPIO.add_event_detect(dt_pin, GPIO.BOTH, callback=self._dt_callback)

    if sw_pin:
      GPIO.setup(sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
      GPIO.add_event_detect(sw_pin, GPIO.FALLING, callback=self._sw_callback)

  def reset(self):
    self._counter = 0

  def _clk_callback(self, channel):
    state = GPIO.input(channel)
    if self._clk_last_state == state:
      return

    if state == 0 and self._dt_last_state == 1:
      self._counter -= 1
      self.logger.info('[{0}] rotated counterclockwise (value={1})'.format(
          self._name, self._counter))
      self.emit('rotate', Direction.COUNTERCLOCKWISE, self._counter)
      self.emit('counterclockwise')
    self._clk_last_state = state

  def _dt_callback(self, channel):
    state = GPIO.input(channel)
    if self._dt_last_state == state:
      return

    if state == 0 and self._clk_last_state == 1:
      self._counter += 1
      self.logger.info('[{0}] rotated clockwise (value={1})'.format(
          self._name, self._counter))
      self.emit('rotate', Direction.CLOCKWISE, self._counter)
      self.emit('clockwise')
    self._dt_last_state = state

  def _sw_callback(self, channel):
    self.logger.info('[{0}] pushed.'.format(self._name))
    self.emit('push')


class DualRotaryEncoder(pattern.EventEmitter, pattern.Logger):
  """Class for pushable dual rotary encoder.

  Events:
    "large_rotate": triggered when large rotary encoder is rotated.
      direction (Direction)
      value (int)
    "small_rotate": triggered when small rotary encoder is rotated.
      direction (Direction)
      value (int)
    "large_clockwise": triggered when large rotary encoder is rotated clockwise for one step.
    "large_counterclockwise": triggered when large rotary encoder is rotated counter clockwise for one step.
    "small_clockwise": triggered when small rotary encoder is rotated clockwise for one step.
    "small_counterclockwise": triggered when small rotary encoder is rotated counter clockwise for one step.
    "push": triggered when rotary encoder is pushed.
  """

  def __init__(self, name, large_clk_pin, large_dt_pin, small_clk_pin,
               small_dt_pin, sw_pin, *args, **kwargs):
    super(DualRotaryEncoder, self).__init__(self, *args, **kwargs)
    self._name = name
    self._large_clk_pin = large_clk_pin
    self._large_dt_pin = large_dt_pin
    self._small_clk_pin = small_clk_pin
    self._small_dt_pin = small_dt_pin
    self._states = {}
    self._large_counter = 0
    self._small_counter = 0

    GPIO.setmode(GPIO.BCM)
    for pin in [large_clk_pin, large_dt_pin, small_clk_pin, small_dt_pin]:
      GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
      GPIO.add_event_detect(pin, GPIO.BOTH, callback=self._callback)
      self._states[pin] = GPIO.input(pin)
    if sw_pin:
      GPIO.setup(sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
      GPIO.add_event_detect(sw_pin, GPIO.FALLING, callback=self._on_pushed)

  def reset(self):
    self._large_counter = 0
    self._small_counter = 0

  def _on_pushed(self, channel):
    self.logger.info('{0}: pushed'.format(self._name))
    self.emit('push')

  def _callback(self, channel):
    state = GPIO.input(channel)
    if state == self._states[channel]:
      return

    if channel == self._large_clk_pin:
      if state != self._states[self._large_dt_pin]:
        self._large_counter += 1
        self.logger.info(
            '[{0}] [large knob] rotated clockwise (value={1})'.format(
                self._name, self._large_counter))
        self.emit('large_rotate', Direction.CLOCKWISE, self._large_counter)
        self.emit('large_clockwise')
    elif channel == self._large_dt_pin:
      if state != self._states[self._large_clk_pin]:
        self._large_counter -= 1
        self.logger.info(
            '[{0}] [large knob] rotated counterclockwise (value={1})'.format(
                self._name, self._large_counter))
        self.emit('large_rotate', Direction.COUNTERCLOCKWISE,
                  self._large_counter)
        self.emit('large_counterclockwise')
    elif channel == self._small_clk_pin:
      if state != self._states[self._small_dt_pin]:
        self._small_counter += 1
        self.logger.info(
            '[{0}] [small knob] rotated clockwise (value={1})'.format(
                self._name, self._small_counter))
        self.emit('small_rotate', Direction.CLOCKWISE, self._small_counter)
        self.emit('small_clockwise')
    elif channel == self._small_dt_pin:
      if state != self._states[self._small_clk_pin]:
        self._small_counter -= 1
        self.logger.info(
            '[{0}] [small knob] rotated counterclockwise (value={1})'.format(
                self._name, self._small_counter))
        self.emit('small_rotate', Direction.COUNTERCLOCKWISE,
                  self._small_counter)
        self.emit('small_counterclockwise')

    self._states[channel] = state