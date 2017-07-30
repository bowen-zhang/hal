import math
import smbus
import sys
import time
import threading

from common import data_filters
from common import pattern
from common import unit


class AirspeedSensor(pattern.Worker, pattern.EventEmitter):
  _AIRSPEED_WINDOW_SIZE = 1000
  _TEMPERATURE_WINDOW_SIZE = 100
  _ADDRESS = 0x28
  _PASCAL_PER_PSI = 6894.76
  _MPH_PER_MPS = 2.3694
  _MAX_PRESSURE = 1 * _PASCAL_PER_PSI   # 1 psi
  _MIN_PRESSURE = -1 * _PASCAL_PER_PSI  # -1 psi
  _PRESSURE_BITS = 14 # 14 bits, 0-16383
  _MAX_TEMPERATURE = 150 # 150 C
  _MIN_TEMPERATURE = -50 # -50 C
  _TEMPERATURE_BITS = 11 # 11 bits, 0-2047

  def __init__(self, *args, **kwargs):
    super(AirspeedSensor, self).__init__(*args, **kwargs)
    self._bus = None
    self._pressure = data_filters.SmoothValue(self._AIRSPEED_WINDOW_SIZE)
    self._temperature = data_filters.SmoothValue(self._TEMPERATURE_WINDOW_SIZE)

  @property
  def raw_pressure(self):
    """ Gets smoothed raw pressure count reading from sensor.

    Returns:
      Pressure count in range of 0-16383.
    """
    return self._pressure.value

  @property
  def pressure(self):
    """ Gets smoothed pressure reading.

    The following formmula is used per MS4525DO datasheet:
      raw_reading = (80% * 16383) / (Pmax - Pmin) * (pressure - Pmin) + 10% * 16383

    Returns:
      Pressure instance representing current pressure.
    """
    value = float(self._pressure.value)
    value -= 0.1 * (2**self._PRESSURE_BITS - 1)
    value *= self._MAX_PRESSURE - self._MIN_PRESSURE
    value /= 0.8 * (2**self._PRESSURE_BITS - 1)
    value += self._MIN_PRESSURE
    return unit.Pressure(value, unit.Pressure.PA)

  @property
  def airspeed(self):
    """ Gets smoothed indicated airspeed reading.

    The following formula is used sea level and standard atmosphere:
      dynamic pressure = 0.5 * fluid density * velocity^2
    where:
      dynamic pressure [N/m^2 or Pascal]
      fluid density = 1.225 [kg/m^3]
      velocity [m/s]

    """
    p = self.pressure
    v = math.sqrt(abs(p) / 0.5 / 1.225) * (1 if p > 0 else -1)
    v *= self._MPH_PER_MPS
    return unit.Speed(unit.Length(v, unit.Length.METER), unit.ONE_SECOND)

  @property
  def temperature(self):
    """ Gets smoothed temperature reading.

    The following formula is used per MS4525DO datasheet:
      raw_reading = (temperature - (Tmin)) * 2047 / (Tmax - (Tmin))
    where:
      Tmin = -50C
      Tmax = 150C

    Returns:
      Temperature instance representing current temperature.
    """
    value = float(self._temperature.value)
    value *= (self._MAX_TEMPERATURE - self._MIN_TEMPERATURE)
    value /= 2**self._TEMPERATURE_BITS - 1
    value += self._MIN_TEMPERATURE
    return unit.Temperature(value, unit.Temperature.CELSIUS)

  def _on_start(self):
    self._pressure.reset()
    self._temperature.reset()
    self._bus = smbus.SMBus(1)

  def _on_run(self):
    data = self._bus.read_i2c_block_data(self._ADDRESS, 4)
    # status == b00: normal operation and a good data packet
    # status == b10: stale data that has been already fetched
    status = (data[0] >> 6) & 0x03
    if status == 0:
      raw_pressure = ((data[0] & 0x3f) << 8) | data[1]
      raw_temperature = (data[2] << 3) | (data[3] >> 5)
      self._pressure.set(raw_pressure)
      self._temperature.set(raw_temperature)
      self.emit('data', self)
