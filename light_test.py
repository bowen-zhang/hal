import time

from hal import light

l = light.Blinkt()
l.on()
time.sleep(2)
l.dim(0.2)
time.sleep(2)
l.dim(1.0)
time.sleep(2)
l.set_color_temperature(2700)
time.sleep(2)
l.set_color_temperature(5500)
time.sleep(2)
l.off()
time.sleep(2)
