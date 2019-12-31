import curses
import logging
import signal
import sys
import time

from . import neo7m

stdscr = None
gps = neo7m.Gps.get_instance()


# Capture SIGINT for cleanup when the script is aborted
def terminate(signal, frame):
  global gps
  print('Exiting...')
  gps.stop()
  exit(0)


def test_neo7m(*args):
  gps.on('update', on_update)
  while True:
    time.sleep(1)


def on_update(gps):
  global stdscr
  stdscr.addstr(0, 0, 'time={0}, mode={1}'.format(gps.utc, gps.mode))
  stdscr.addstr(1, 0, 'Lat={0}, Lon={1}, Alt={2}'.format(
      gps.latitude, gps.longitude, gps.altitude))
  stdscr.addstr(2, 0, 'Speed={0}, Track={1}, Vertical Speed={2}'.format(
      gps.ground_speed, gps.ground_course, gps.vertical_speed))
  stdscr.refresh()


if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  signal.signal(signal.SIGINT, terminate)
  global stdscr
  stdscr = curses.initscr()
  curses.noecho()
  curses.wrapper(test_neo7m)
