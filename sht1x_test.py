import time
import RPi.GPIO as GPIO

from common import console
from hal import sht1x

dash = console.Dashboard.get_instance()
temp_field = console.LabeledTextField(
    x=1, y=1, max_width=30, label='Temperature: ', fmt='{0:.1f}C')
dewpoint_field = console.LabeledTextField(
    x=1, y=2, max_width=30, label='Dewpoint: ', fmt='{0:.1f}C')
humidity_field = console.LabeledTextField(
    x=1, y=3, max_width=30, label='Humidity: ', fmt='{0:.1f}%')
latency_field = console.LabeledTextField(
    x=40, y=1, max_width=30, label='Latency: ', fmt='{0:.0f}ms')

with sht1x.SHT1x() as sensor:
  while True:
    t0 = time.time()
    temp = sensor.read_temperature()
    humidity = sensor.read_humidity(temp)
    dewpoint = sensor.calculate_dew_point(temp, humidity)
    t1 = time.time()
    temp_field.set(temp)
    humidity_field.set(humidity)
    dewpoint_field.set(dewpoint)
    latency_field.set((t1 - t0) * 1000)
    time.sleep(0.5)
