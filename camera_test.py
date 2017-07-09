import signal
import sys
import time

from blackbox.devices import camera
from common import clocks

c = camera.Camera(clock=clocks.SystemClock())

def terminate(signal, frame):
    c.stop()
    c.close()
    sys.exit(0)

def test():
    c.start_recording('video.h264')
    time.sleep(5)
    c.capture('image1.jpg')
    time.sleep(5)
    c.capture('image2.jpg')
    time.sleep(5)
    c.stop_recording()
    c.close()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, terminate)
    test()
