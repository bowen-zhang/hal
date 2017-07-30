import logging
import os
import sys
import time

from hal import ms4525do

last_update = None

def on_data(sensor):
  if not last_update or time.time() - last_update > 0.1:
    sys.stdout.write('\x1b7\x1b[1;1fRaw Pressure = %s\t\x1b8' % sensor.raw_pressure)
    sys.stdout.write('\x1b7\x1b[2;1fPressure = {0:.1f} Pa   \x1b8'.format(sensor.pressure.pa))
    sys.stdout.write('\x1b7\x1b[3;1fAirspeed = {0:.0f} mph   \x1b8'.format(sensor.airspeed.mph))
    sys.stdout.write('\x1b7\x1b[4;1fTemperature = {0:.1f} C   \x1b8'.format(sensor.temperature.c))
    sys.stdout.write('\x1b7\x1b[5;1f%s\t\x1b8' % time.time())
    sys.stdout.flush()
    last_update = time.time()

def test():
  os.system('clear')
  sensor = ms4525do.AirspeedSensor()
  sensor.start()
  sensor.on('data', on_data)
  try:
    while True:
      #speed = int(raw_input('Speed:'))
      time.sleep(1)
  finally:
    sensor.stop()

if __name__ == '__main__':
  logging.basicConfig()
  test()