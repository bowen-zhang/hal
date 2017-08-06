import logging
import os
import sys
import time

from common import console
from hal import ms4525do

dash = console.Dashboard.get_instance()
raw_pressure_field = console.LabeledTextField(
    dash, x=1, y=1, max_width=30, label='Raw Pressure: ', fmt='{0:.1f} count')
pressure_field = console.LabeledTextField(
    dash, x=1, y=2, max_width=30, label='Pressure: ', fmt='{0:.1f} Pa')
airspeed_field = console.LabeledTextField(
    dash, x=1, y=3, max_width=30, label='Airspeed: ', fmt='{0:.0f} mph')
temperature_field = console.LabeledTextField(
    dash, x=1, y=4, max_width=30, label='Temperature: ', fmt='{0:.1f} C')
fetch_latency_field = console.LabeledTextField(
    dash, x=31, y=1, max_width=30, label='Fetch Latency: ', fmt='{0:.4f} sec')
total_latency_field = console.LabeledTextField(
    dash, x=31, y=2, max_width=30, label='Total Latency: ', fmt='{0:.4f} sec')

last_update = time.time()


def on_data(sensor):
  global last_update
  if time.time() - last_update > 0.1:
    dash.start_update()
    raw_pressure_field.set(sensor.raw_pressure)
    pressure_field.set(sensor.pressure.pa)
    airspeed_field.set(sensor.airspeed.mph)
    temperature_field.set(sensor.temperature.c)
    fetch_latency_field.set(sensor.fetch_latency)
    total_latency_field.set(sensor.total_latency)
    dash.stop_update()

    last_update = time.time()


def test():
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
