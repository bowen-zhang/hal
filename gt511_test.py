import logging
import time

from hal import gt511


def enroll(scanner):
  print 'Enrolling...'
  if scanner.is_enrolled(0):
    scanner.delete_position(0)
  scanner.enroll(0)
  print 'Done!'


def identify(scanner):
  try:
    pos = scanner.identify()
    print 'Identified as #{0}.'.format(pos)
  except:
    print 'Unknown'


def capture(scanner):
  print 'Scanning...'
  scanner.scan()
  scanner.set_cmos_led(False)
  img = scanner.get_image()
  img.save('1.png')
  print 'Saved image.'


def test_gt511():
  scanner = gt511.FingerprintScanner()
  scanner.initialize()
  scanner.change_baudrate(115200)
  try:
    scanner.set_cmos_led(True)
    print 'Ready to scan...'
    while not scanner.is_finger_pressed():
      time.sleep(0.5)

    identify(scanner)
    # capture(scanner)
  except Exception as e:
    print 'exception: {0}'.format(e)
  finally:
    scanner.close()


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  test_gt511()
