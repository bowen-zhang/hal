import abc
import datetime
import enum
import pynmea2
import serial
import sys
import threading
import time

from common import pattern
from common import unit


class GpsMode(enum.Enum):
  GPS_NO_FIX = 1
  GPS_2D_FIX = 2
  GPS_3D_FIX = 3


def calc_checksum(data):
  a = 0
  b = 0
  for i in data:
    a = a + ord(i)
    b = b + a
  return chr(a & 0xff) + chr(b & 0xff)


def write(s, data):
  data = '\xB5\x62' + data + calc_checksum(data)
  size = s.write(data)
  s.flush()
  time.sleep(0.1)


def detect_baudrate():
  print 'Detecting GPS baud rate...'
  baud_rates = [115200, 57600, 9600, 19200, 38400]
  for baud_rate in baud_rates:
    print 'Attempting {0}...'.format(baud_rate)
    with serial.Serial('/dev/ttyS0', baud_rate) as s:
      deadline = time.time() + 3
      while time.time() < deadline:
        buf = s.read(1024)
        if '\r\n$GP' in buf:
          return baud_rate

  raise 'Unable to detect GPS baud rate.'


def init_gps():
  #baud_rate = detect_baudrate()
  baud_rate = 9600
  if baud_rate != 115200:
    print 'Setting GPS baud rate to 115200...'
    with serial.Serial('/dev/ttyS0', baud_rate) as s:
      write(s, '\x06\x00\x14\x00' + '\x01\x00\x00\x00\xD0\x08\x00\x00' +
            '\x00\xC2\x01\x00\x07\x00\x03\x00' + '\x00\x00\x00\x00')

  print 'Setting GPS update rate to 10HZ...'
  with serial.Serial('/dev/ttyS0', 115200) as s:
    write(s, '\x06\x08\x06\x00' + '\x64\x00\x01\x00\x01\x00')


def read():
  with serial.Serial('/dev/ttyS0', 115200) as s:
    while True:
      if s.isOpen():
        while s.inWaiting() > 0:
          sys.stdout.write(s.read())


class Gps(pattern.Singleton, pattern.EventEmitter, pattern.Worker):

  def __init__(self, *args, **kwargs):
    super(Gps, self).__init__(*args, **kwargs)

    init_gps()
    self._ser = None
    self._mode = None
    self._timestamp = None
    self._lon = None
    self._lat = None
    self._alt = None
    self._truck = None
    self._speed = None
    self._climb = None
    self._mag_var = None
    self._gsv = []
    self.__satellites_in_view = 0
    self.start()

  @property
  def ready(self):
    return self._mode and self._mode == 3

  @property
  def mode(self):
    if self._mode:
      return GpsMode(self._mode)
    else:
      return None

  @property
  def utc(self):
    return self._timestamp

  @property
  def satellites_in_view(self):
    return self._satellites_in_view

  @property
  def longitude(self):
    if self._lon:
      return unit.Angle(self._lon, unit.Angle.DEGREE,
                        unit.Angle.LONGITUDE_RANGE)
    else:
      return None

  @property
  def latitude(self):
    if self._lat:
      return unit.Angle(self._lat, unit.Angle.DEGREE,
                        unit.Angle.LATITUDE_RANGE)
    else:
      return None

  @property
  def altitude(self):
    if self._alt:
      return unit.Length(self._alt, unit.Length.METER)
    else:
      return None

  @property
  def ground_course(self):
    if self._truck:
      return unit.Angle(self._track, unit.Angle.DEGREE,
                        unit.Angle.HEADING_RANGE)
    else:
      return None

  @property
  def ground_speed(self):
    if self._speed:
      return unit.Speed(
          unit.Length(self._speed, unit.Length.NAUTICAL_MILE), unit.ONE_HOUR)
    else:
      return None

  @property
  def vertical_speed(self):
    if self._climb:
      return unit.Speed(
          unit.Length(self._climb, unit.Length.METER), unit.ONE_SECOND)
    else:
      return None

  @property
  def magnetic_variation(self):
    if self._mag_var:
      return unit.Angle(self._mag_var, unit.Angle.DEGREE,
                        unit.Angle.RELATIVE_RANGE)
    else:
      return None

  def close(self):
    super(self.__class__, self).close()

  def _on_start(self):
    assert not self._ser

    self._ser = serial.Serial('/dev/ttyS0', 115200)
    self._reader = pynmea2.NMEAStreamReader()

  def _on_run(self):
    data = self._ser.read(16).replace('\r', '')
    try:
      msgs = self._reader.next(data)
      for msg in msgs:
        if type(msg) == pynmea2.types.talker.GLL:
          # Loran emulation
          pass
        elif type(msg) == pynmea2.types.talker.RMC:
          # Recommended minimum specific GPS/TRANSIT data
          self._timestamp = msg.datetime
          self._lat = msg.latitude  # degree
          self._lon = msg.longitude  # degree
          self._track = msg.true_course  # degree (True)
          self._speed = msg.spd_over_grnd  # knots
          if msg.mag_var_dir and msg.mag_variation:
            if msg.mag_var_dir == 'W':
              self._mag_var = float(msg.mag_variation)  # degree
            else:
              self._mag_var = -float(msg.mag_variation)  # degree
          self.emit('update', self)
        if type(msg) == pynmea2.types.talker.VTG:
          # Vector track and speed over ground
          pass
        elif type(msg) == pynmea2.types.talker.GGA:
          # fix data
          # msg.gps_qual: 0=invalid, 1=gps fix
          self._alt = msg.altitude
        elif type(msg) == pynmea2.types.talker.GSA:
          # Satellite data
          self._mode = int(msg.mode_fix_type)
        elif type(msg) == pynmea2.types.talker.GSV:
          # Satellites in view
          if msg.num_messages != len(self._gsv):
            self._gsv = [0] * int(msg.num_messages)
          self._gsv[int(msg.msg_num) - 1] = int(msg.num_sv_in_view)
          self._satellites_in_view = sum(self._gsv)

    except Exception as e:
      self.logger.warn(str(e))

  def _on_stop(self):
    if self._ser:
      self._ser.close()
      self._ser = None


if __name__ == '__main__':
  init_gps()
  read()
