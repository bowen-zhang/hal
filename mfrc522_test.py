import logging
import signal
import sys

import mfrc522

# Create an object of the class MFRC522
controller = mfrc522.RFIDController()
reader = mfrc522.RFIDReader(controller=controller)


def terminate(signal, frame):
  global reader
  print 'Exiting...'
  reader.stop()
  exit(0)


signal.signal(signal.SIGINT, terminate)


def test_rfid():
  reader.on('card', _on_card)
  signal.pause()


def _on_card(card):
  print "Card read UID: {0:X}".format(card.uid)

  card.select_tag()
  card.authenticate(4)
  print 'Block 4: {0}'.format(card.read(4))
  print 'Block 5: {0}'.format(card.read(5))

  if sys.argv[1] == 'write':
    print 'Writing...'
    card.write_str(block=4, value='John Parker')
    card.write_int32(block=5, offset=0, value=-1)
    print 'Done'
    print 'Block 4: {0}'.format(card.read(4))
    print 'Block 5: {0}'.format(card.read(5))


if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  test_rfid()
