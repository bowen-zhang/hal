import time

from common import console
from common import unit
from hal import bmp180

dash = console.Dashboard.get_instance()
temp_field = console.LabeledTextField(
    x=1, y=1, max_width=30, label='Temperature: ', fmt='{0:.1f}C')
pressure_field = console.LabeledTextField(
    x=1, y=2, max_width=30, label='Pressure: ', fmt='{0:.2f}inHG')
latency_field = console.LabeledTextField(
    x=40, y=1, max_width=30, label='Latency: ', fmt='{0:.0f}ms')


def main():
  sensor = bmp180.PressureSensor()
  while True:
    t0 = time.time()
    sensor.read()
    t1 = time.time()
    temp_field.set(sensor.temperature.c)
    pressure_field.set(sensor.pressure.inhg)
    latency_field.set((t1 - t0) * 1000)


if __name__ == "__main__":
  main()
