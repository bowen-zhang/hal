import logging
import subprocess

from hal import mobile


def test_mobile():
  m = mobile.Mobile()
  try:
    m.connect()
    print 'Pinging google.com...'
    mobile.ping('google.com')
    print 'Ping succeeded.'
    m.disconnect()
  except Exception as e:
    m.disconnect()
    print e


if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  test_mobile()
