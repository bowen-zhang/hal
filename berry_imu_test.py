import signal
import sys
import time

from . import berry_imu

abort = False

def terminate(signal, frame):
    global abort
    print('Exiting...')
    abort = True

def test_g_load():
    load = berry_imu.Load()
    while not abort:
        s = '\rX={0:.1f}G, Y={1:.1f}, Z={2:.1f}G    '.format(load.x, load.y, load.z)
        sys.stdout.write(s)
        sys.stdout.flush()
        time.sleep(0.1)

def test_environment():
    env = berry_imu.Environment()
    while not abort:
        (t, p) = env.temperature_pressure
        s = '\rTemp={0:.1f}F, Pressure={1:.2f}in    '.format(t.f, p.inhg)
        sys.stdout.write(s)
        sys.stdout.flush()
        time.sleep(0.3)

def test_attitude():
    attitude = berry_imu.Attitude()
    while not abort:
        s = '\rPitch={0:.0f}, Roll={1:.0f}, Heading={2:.0f}    '.format(attitude.pitch.degree, attitude.roll.degree, attitude.heading.degree)
        sys.stdout.write(s)
        sys.stdout.flush()
        time.sleep(0.3)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, terminate)
    #test_g_load()
    #test_environment()
    test_attitude()
