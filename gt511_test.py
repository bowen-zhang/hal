import logging
import time

from hal import gt511


def enroll(scanner):
  position = input('Position to enroll: ')
  print 'Place finger on scanner now.'
  scanner.wait_for_finger()
  print 'Enrolling...'
  if scanner.is_enrolled(position):
    scanner.delete_position(position)
  scanner.enroll(position)
  print 'Done!'


def identify(scanner):
  print 'Place finger on scanner now.'
  scanner.wait_for_finger()
  try:
    pos = scanner.identify()
    print 'Identified as #{0}.'.format(pos)
  except:
    print 'Unknown'


def capture(scanner):
  print 'Place finger on scanner now.'
  scanner.wait_for_finger()
  print 'Scanning...'
  scanner.capture()
  img = scanner.get_image()
  img.save('1.png')
  print 'Saved image.'


def test_gt511():
  scanner = gt511.FingerprintScanner()
  scanner.initialize()
  scanner.change_baudrate(115200)

  state = ''
  for i in range(20):
    state += '[x]' if scanner.is_enrolled(i) else '[ ]'
  print 'Enrollment: ' + state
  try:
    scanner.set_cmos_led(True)
    while True:
      print 'Options:'
      print '  1. Enroll'
      print '  2. Identify'
      print '  3. Capture'
      print '  0. Exit'
      option = input('Please choose: ')
      if option == 0:
        break
      elif option == 1:
        enroll(scanner)
      elif option == 2:
        identify(scanner)
      elif option == 3:
        capture(scanner)
  except Exception as e:
    print 'exception: {0}'.format(e)
  finally:
    scanner.set_cmos_led(False)
    scanner.close()


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  test_gt511()
