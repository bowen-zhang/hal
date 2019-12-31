import logging
import time

from hal import gt511


def enroll(scanner):
  position = eval(input('Position to enroll: '))
  print('Place finger on scanner now.')
  scanner.set_cmos_led(True)
  scanner.wait_for_finger()
  print('Enrolling...')
  if scanner.is_enrolled(position):
    scanner.delete_position(position)
  scanner.enroll(position)
  scanner.set_cmos_led(False)
  print('Done!')


def identify(scanner):
  print('Place finger on scanner now.')
  scanner.set_cmos_led(True)
  scanner.wait_for_finger()
  pos = scanner.identify()
  if pos >= 0:
    print('Identified as #{0}.'.format(pos))
  else:
    print('Unknown')
  scanner.set_cmos_led(False)


def capture(scanner):
  print('Place finger on scanner now.')
  scanner.set_cmos_led(True)
  scanner.wait_for_finger()
  print('Scanning...')
  img = scanner.get_image()
  img.save('1.png')
  print('Saved image.')
  scanner.set_cmos_led(False)


def test_gt511():
  scanner = gt511.FingerprintScanner()
  scanner.initialize()

  state = ''
  for i in range(20):
    state += '[x]' if scanner.is_enrolled(i) else '[ ]'
  print('Enrollment: ' + state)
  try:
    while True:
      print('Options:')
      print('  1. Enroll')
      print('  2. Identify')
      print('  3. Capture')
      print('  0. Exit')
      option = eval(input('Please choose: '))
      if option == 0:
        break
      elif option == 1:
        enroll(scanner)
      elif option == 2:
        identify(scanner)
      elif option == 3:
        capture(scanner)
  except Exception as e:
    print('exception: {0}'.format(e))
  finally:
    scanner.set_cmos_led(False)
    scanner.close()


def test_monitor():
  monitor = gt511.FingerprintMonitor()
  monitor.start()
  print('Waiting...')
  try:
    while True:
      time.sleep(1)
  finally:
    monitor.stop()


if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  test_gt511()
  #test_monitor()
