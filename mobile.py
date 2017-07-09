import datetime
import re
import signal
import subprocess
import threading
import time

from common import pattern


def ping(host):
  exitcode = subprocess.call(['ping', '-c', '1', '-I', 'ppp0', host])
  if exitcode != 0:
    raise Exception('Failed to ping {0}.'.format(host))


class Mobile(pattern.EventEmitter, pattern.Logger, pattern.Singleton):
  CONNECT_TIMEOUT = datetime.timedelta(seconds=60)

  def __init__(self, *args, **kwargs):
    super(Mobile, self).__init__(*args, **kwargs)

    self._proc = None
    self._thread = None
    self._connectedEvent = threading.Event()

  def connect(self):
    self.logger.info('Connecting to 3g network...')
    self._connectedEvent.clear()
    self._proc = subprocess.Popen(['sudo', 'wvdial'], stderr=subprocess.PIPE)
    self._thread = threading.Thread(target=self._watch)
    self._thread.daemon = True
    self._thread.start()
    if not self._connectedEvent.wait(Mobile.CONNECT_TIMEOUT.total_seconds()):
      self.disconnect()
      raise Exception('Timeout while connecting to 3g network.')

    time.sleep(1)
    self.logger.info('Connected to 3g network.')
    self.emit('connected', self)

  def disconnect(self):
    self.logger.info('Disconnecting from 3g network...')
    if self._proc:
      subprocess.call(['sudo', 'kill', '-15', str(self._proc.pid)])
      self._proc.wait()
      self._proc = None
    if self._thread:
      self._thread.join()
      self._thread = None
    self.logger.info('Disconnected from 3g network.')
    self.emit('disconnected', self)

  def _watch(self):
    try:
      while self._proc:
        line = self._proc.stderr.readline().strip()
        if line:
          if re.search('local\s+IP address', line):
            self._connectedEvent.set()
    except IOError:
      pass
