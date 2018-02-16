from hal import motion
import time


def on_motion(has_motion):
  print '{0}: {1}'.format(time.time(), 'Detected' if has_motion else 'Gone')


with motion.PIRMotionSensor(pin=14) as m:
  m.on('motion', on_motion)
  m.start()
  while True:
    time.sleep(100)
