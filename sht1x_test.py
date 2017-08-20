import time
import RPi.GPIO as GPIO
from hal import sht1x

DATA_PIN = 18
SCK_PIN = 23

with sht1x.SHT1x(DATA_PIN, SCK_PIN, gpio_mode=GPIO.BCM) as sensor:
	for i in range(5):
	    temp = sensor.read_temperature()
	    humidity = sensor.read_humidity(temp)
	    sensor.calculate_dew_point(temp, humidity)
	    print(sensor)
	    time.sleep(2)