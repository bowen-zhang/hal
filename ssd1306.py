import os
import threading

from luma.core import serial
from luma.oled import device
from luma.core import render
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw

from common import pattern


class Display(pattern.Singleton):

  def __init__(self, *args, **kwargs):
    super(Display, self).__init__(*args, **kwargs)

    self._serial = serial.i2c(port=1, address=0x3C)
    self._device = device.ssd1306(
        self._serial, width=128, height=64, rotate=0, mode='RGB')
    self._image = Image.new(self._device.mode, self._device.size)
    self._draw = ImageDraw.Draw(self._image)

    font_path = os.path.join(
        os.path.dirname(__file__), 'RobotoMono-Regular.ttf')
    self._font = ImageFont.truetype(font_path, 11)

    self._lock = threading.Lock()

  def clear(self, x0=0, y0=0, x1=127, y1=63):
    self._lock.acquire()
    try:
      self._clear(x0, y0, x1, y1)
    finally:
      self._lock.release()

  def text(self, x, y, msg, color='white'):
    self._lock.acquire()
    try:
      size = self._draw.textsize(msg, font=self._font)
      self._clear(x, y, x + size[0], y + size[1])
      self._draw.text((x, y), msg, font=self._font, fill=color)
      self._refresh()
    finally:
      self._lock.release()

  def rectangle(self, x0, y0, x1, y1, fill='black', outline='white'):
    self._lock.acquire()
    try:
      self._draw.rectangle([x0, y0, x1, y1], fill=fill, outline=outline)
      self._refresh()
    finally:
      self._lock.release()

  def _clear(self, x0, y0, x1, y1):
    self._draw.rectangle([x0, y0, x1, y1], fill='black', outline='black')

  def _refresh(self):
    self._device.display(self._image)
