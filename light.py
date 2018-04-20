import blinkt
import math
import threading
import time


class Light(object):
  def on(self):
    pass

  def off(self):
    pass


class DimmableLight(Light):
  def dim(self, brightness):
    pass


class Blinkt(DimmableLight):
  """HAL class for Blinkt LED lights.

  Prerequisites:
    sudo apt-get install python-blinkt
  """
  _INTERVAL = 0.01  # sec
  _MAX_COLOR_CHANGE_DURATION = 1.0  # sec
  _MAX_BRIGHTNESS_CHANGE_DURATION = 1.0  # sec
  _COLOR_STEP = 255 / (Blinkt._MAX_COLOR_CHANGE_DURATION / Blinkt._INTERVAL)
  _BRIGHTNESS_STEP = 1.0 / (
      Blinkt._MAX_BRIGHTNESS_CHANGE_DURATION / Blinkt._INTERVAL)

  def __init__(self):
    self._current = (0, 0, 0, 0)
    self._target = (0, 0, 0, 0)
    self._lock = threading.Lock()
    self._signal = threading.Event()
    self._abort = False
    self._worker = threading.Thread(target=self._run)

  def close(self):
    self._lock.acquire()
    self._abort = True
    self._signal.set()
    self._lock.release()

  def on(self):
    self._lock.acquire()
    self._target = (255, 255, 255, 0.5)
    self._signal.set()
    self._lock.release()

  def off(self):
    self._lock.acquire()
    self._target = (0, 0, 0, 0.0)
    self._signal.set()
    self._lock.release()

  def dim(self, brightness):
    """Set brightness of all LEDs.

    Args:
      brightness: 0-1.0
    """
    self._lock.acquire()
    self._target[3] = brightness
    self._signal.set()
    self._lock.release()

  def set_color_temperature(color_temperature):
    r, g, b = _convert_K_to_RGB(color_temperature)
    self._lock.acquire()
    self._target = (r, g, b, self._target[3])
    self._signal.set()
    self._lock.release()

  def _run(self):
    step = [
        Blinkt._COLOR_STEP, Blinkt._COLOR_STEP, Blinkt._COLOR_STEP,
        Blinkt._BRIGHTNESS_STEP
    ]
    while self._signal.wait() and not self._abort:
      self._lock.acquire()

      for i in range(4):
        if self._current[i] < self._target[i]:
          self._current[i] = min(self._current[i] + step[i], self._target[i])
        else:
          self._current[i] = max(self._current[i] - step[i], self._target[i])
      blinkt.set_all(self._current)
      blinkt.show()

      if self._current == self._target:
        self._signal.clear()

      self._lock.release()
      time.sleep(blinkt._INTERVAL)


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