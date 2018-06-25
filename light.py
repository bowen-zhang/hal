import blinkt
import math
import threading
import time

from common import pattern


class Light(object):

  def on(self):
    pass

  def off(self):
    pass


class DimmableLight(Light):

  def dim(self, brightness):
    pass


class Blinkt(DimmableLight, pattern.Closable):
  """HAL class for Blinkt LED lights.

  Prerequisites:
    sudo apt-get install python-blinkt
  """
  _INTERVAL = 0.01  # sec
  _MAX_COLOR_CHANGE_DURATION = 1.0  # sec
  _MAX_BRIGHTNESS_CHANGE_DURATION = 1.0  # sec
  _STEP = [
      255 / (Blinkt._MAX_COLOR_CHANGE_DURATION / Blinkt._INTERVAL),
      255 / (Blinkt._MAX_COLOR_CHANGE_DURATION / Blinkt._INTERVAL),
      255 / (Blinkt._MAX_COLOR_CHANGE_DURATION / Blinkt._INTERVAL),
      1.0 / (Blinkt._MAX_BRIGHTNESS_CHANGE_DURATION / Blinkt._INTERVAL),
  ]

  def __init__(self, *args, **kwargs):
    super(Blinkt, self).__init__(*args, **kwargs)
    self._current = (0, 0, 0, 0)
    self._target = (0, 0, 0, 0)
    self._lock = threading.Lock()
    self._thread = None
    self._abort = threading.Event()

  def close(self):
    if self._thread:
      self._abort.set()
      self._thread.join()
      self._thread = None

  def on(self):
    self._make_change(255, 255, 255, 0.5)

  def off(self):
    self._make_change(0, 0, 0, 0.0)

  def dim(self, brightness):
    """Set brightness of all LEDs.

    Args:
      brightness: 0-1.0
    """
    self._make_change(brightness=brightness)

  def set_color_temperature(color_temperature):
    r, g, b = _convert_K_to_RGB(color_temperature)
    self._make_change(r, g, b)

  def _make_change(self, r=None, g=None, b=None, brightness=None):
    self._target[0] = r if r else self._target[0]
    self._target[1] = g if g else self._target[1]
    self._target[2] = b if b else self._target[2]
    self._target[3] = brightness if brightness else self._target[3]

    with self._lock:
      if self._thread:
        self._abort.set()
        self._thread.join()
      self._abort.clear()
      self._target = new_values
      self._thread = threading.Thread(name='Blinkt', target=self._transient)
      self._thread.daemon = False
      self._thread.start()

  def _run(self):
    while True:
      if self._abort.wait(self._INTERVAL):
        break
      if self._current == self._target:
        break

      for i in range(4):
        if self._current[i] < self._target[i]:
          self._current[i] = min(self._current[i] + self._STEP[i],
                                 self._target[i])
        else:
          self._current[i] = max(self._current[i] - self._STEP[i],
                                 self._target[i])
      blinkt.set_all(self._current)
      blinkt.show()


def _convert_K_to_RGB(colour_temperature):
  """Converts from K to RGB.

    algorithm courtesy of http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/

    Args:
      colour_temperature: in Kevin.
    Returns:
      (red, green, blue)
    """
  #range check
  if colour_temperature < 1000:
    colour_temperature = 1000
  elif colour_temperature > 40000:
    colour_temperature = 40000

  tmp_internal = colour_temperature / 100.0

  # red
  if tmp_internal <= 66:
    red = 255
  else:
    tmp_red = 329.698727446 * math.pow(tmp_internal - 60, -0.1332047592)
    if tmp_red < 0:
      red = 0
    elif tmp_red > 255:
      red = 255
    else:
      red = tmp_red

  # green
  if tmp_internal <= 66:
    tmp_green = 99.4708025861 * math.log(tmp_internal) - 161.1195681661
    if tmp_green < 0:
      green = 0
    elif tmp_green > 255:
      green = 255
    else:
      green = tmp_green
  else:
    tmp_green = 288.1221695283 * math.pow(tmp_internal - 60, -0.0755148492)
    if tmp_green < 0:
      green = 0
    elif tmp_green > 255:
      green = 255
    else:
      green = tmp_green

  # blue
  if tmp_internal >= 66:
    blue = 255
  elif tmp_internal <= 19:
    blue = 0
  else:
    tmp_blue = 138.5177312231 * math.log(tmp_internal - 10) - 305.0447927307
    if tmp_blue < 0:
      blue = 0
    elif tmp_blue > 255:
      blue = 255
    else:
      blue = tmp_blue

  return red, green, blue