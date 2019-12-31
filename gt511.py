"""Library for fingerprint scanner.

To use GT-511C1R fingerprint scanner, make sure:
  1. Enable serial port
  2. Disable serial console
"""

import datetime
import os
import serial
import struct
import sys
import time

from PIL import Image

from common import pattern


class FingerprintScanner(pattern.Logger):

  _IMAGE_SIZE = (240, 216)

  _CMD_STRUCT = '<BBHIH'
  _DATA_STRUCT = lambda self, x: '<BBH' + str(x) + 's'
  _CHECKSUM_STRUCT = '<H'

  _PACKETS = {
      'Command1': 0x55,
      'Command2': 0xAA,
      'Data1': 0x5A,
      'Data2': 0xA5,
      '\x55\xAA': 'C',
      '\x5A\xA5': 'D'
  }

  _COMMANDS = {
      'Open': 0x01,  # Initialization
      'Close': 0x02,  # Termination
      'UsbInternalCheck': 0x03,  # Check if the connected USB device is valid
      'ChangeBaudrate': 0x04,  # Change UART baud rate
      'SetIAPMode':
      0x05,  # Enter IAP Mode. In this mode, FW Upgrade is available
      'CmosLed': 0x12,  # Control CMOS LED
      'GetEnrollCount': 0x20,  # Get enrolled fingerprint count
      'CheckEnrolled':
      0x21,  # Check whether the specified ID is already enrolled
      'EnrollStart': 0x22,  # Start an enrollment
      'Enroll1': 0x23,  # Make 1st template for an enrollment
      'Enroll2': 0x24,  # Make 2nd template for an enrollment
      'Enroll3': 0x25,  # Make 3rd template for an enrollment.
      #    Merge three templates into one template,
      #    save merged template to the database
      'IsPressFinger': 0x26,  # Check if a finger is placed on the sensor
      'DeleteID': 0x40,  # Delete the fingerprint with the specified ID
      'DeleteAll': 0x41,  # Delete all fingerprints from the database
      'Verify':
      0x50,  # 1:1 Verification of the capture fingerprint image with the specified ID
      'Identify':
      0x51,  # 1:N Identification of the capture fingerprint image with the database
      'VerifyTemplate':
      0x52,  # 1:1 Verification of a fingerprint template with the specified ID
      'IdentifyTemplate':
      0x53,  # 1:N Identification of a fingerprint template with the database
      'CaptureFinger':
      0x60,  # Capture a fingerprint image(256x256) from the sensor
      'MakeTemplate': 0x61,  # Make template for transmission
      'GetImage': 0x62,  # Download the captured fingerprint image (256x256)
      'GetRawImage':
      0x63,  # Capture & Download raw fingerprint image (32'\x240)
      'GetTemplate': 0x70,  # Download the template of the specified ID
      'SetTemplate': 0x71,  # Upload the template of the specified ID
      'GetDatabaseStart': 0x72,  # Start database download, obsolete
      'GetDatabaseEnd': 0x73,  # End database download, obsolete
      'UpgradeFirmware': 0x80,  # Not supported
      'UpgradeISOCDImage': 0x81,  # Not supported
      'Ack': 0x30,  # Acknowledge
      'Nack': 0x31  # Non-acknowledge
  }

  _ERRORS = {
      0x1001: 'NACK_TIMEOUT',  # (Obsolete) Capture timeout
      0x1002: 'NACK_INVALID_BAUDRATE',  # (Obsolete) Invalid serial baud rate
      0x1003: 'NACK_INVALID_POS',  # The specified ID is not in range[0,199]
      0x1004: 'NACK_IS_NOT_USED',  # The specified ID is not used
      0x1005: 'NACK_IS_ALREADY_USED',  # The specified ID is already in use
      0x1006: 'NACK_COMM_ERR',  # Communication error
      0x1007: 'NACK_VERIFY_FAILED',  # 1:1 Verification Failure
      0x1008: 'NACK_IDENTIFY_FAILED',  # 1:N Identification Failure
      0x1009: 'NACK_DB_IS_FULL',  # The database is full
      0x100A: 'NACK_DB_IS_EMPTY',  # The database is empty
      0x100B: 'NACK_TURN_ERR',  # (Obsolete) Invalid order of the enrollment
      #    (EnrollStart->Enroll1->Enroll2->Enroll3)
      0x100C: 'NACK_BAD_FINGER',  # Fingerprint is too bad
      0x100D: 'NACK_ENROLL_FAILED',  # Enrollment Failure
      0x100E: 'NACK_IS_NOT_SUPPORTED',  # The command is not supported
      0x100F:
      'NACK_DEV_ERR',  # Device error: probably Crypto-Chip is faulty (Wrong checksum ~Z)
      0x1010: 'NACK_CAPTURE_CANCELED',  # (Obsolete) Capturing was canceled
      0x1011: 'NACK_INVALID_PARAM',  # Invalid parameter
      0x1012: 'NACK_FINGER_IS_NOT_PRESSED',  # Finger is not pressed
  }

  _RESPONSES = {'Ack': 0x30, 'Nack': 0x31, 0x30: 'Ack', 0x31: 'Nack'}

  def __init__(self,
               port='/dev/ttyS0',
               baudrate=9600,
               device_id=0x01,
               timeout=2,
               *args,
               **kwargs):
    super(FingerprintScanner, self).__init__(*args, **kwargs)

    if not os.path.exists(port):
      raise IOError("Port " + port + " cannot be opened!")

    self._device_id = device_id
    self._timeout = timeout
    self._save = False

    self.logger.debug('Opening port {0}...'.format(port))
    self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
    self.logger.debug('Opened port {0}.'.format(port))

    self._serial.flushInput()
    self._serial.flushOutput()

  def initialize(self, detect_baudrate=False):
    self.logger.info('Initializing...')

    if detect_baudrate:
      response = self._detect_baudrate()
    else:
      self._send_command('Open', True)
      response = self._get_response()

    self._device_data = self._get_data(16 + 4 + 4)
    self._serial.timeout = self._timeout
    self._change_baudrate(115200)

  def close(self):
    self.logger.info('Closing...')
    self._change_baudrate(9600)
    try:
      self._send_command('Close')
      self._get_response()
    except FingerprintScannerException:
      pass
    self._serial.flushInput()
    self._serial.flushOutput()
    self._serial.close()
    self._serial = None
    self.logger.info('Closed')

  def set_cmos_led(self, on=False):
    self._send_command('CmosLed', on)
    self._get_response()

  def get_enroll_count(self):
    self._send_command('GetEnrollCount')
    return self._get_response()

  def is_enrolled(self, position):
    self._send_command('CheckEnrolled', position)
    try:
      self._get_response()
      return True
    except FingerprintScannerException:
      return False

  def enroll(self, position):
    self._send_command('EnrollStart', position)
    self._get_response()
    print('Scanning #1...')
    self.capture(best_image=True)
    self._send_command('Enroll1')
    self._get_response()
    print('Lift finger up...')
    while self.is_finger_pressed():
      time.sleep(0.5)
    print('Press finger again...')
    while not self.is_finger_pressed():
      time.sleep(0.5)
    self.capture(best_image=True)
    self._send_command('Enroll2')
    self._get_response()
    print('Lift finger up...')
    while self.is_finger_pressed():
      time.sleep(0.5)
    print('Press finger again...')
    while not self.is_finger_pressed():
      time.sleep(0.5)
    self.capture(best_image=True)
    self._send_command('Enroll3')
    self._get_response()

  def wait_for_finger(self, to_press=True, timeout=None):
    if timeout is not None:
      timeout_secs = timeout.total_seconds()
      while True:
        if self.is_finger_pressed() == to_press:
          return to_press
        if timeout_secs <= 0:
          return not to_press
        time.sleep(0.2 if timeout_secs > 0.2 else timeout_secs)
        timeout_secs -= 0.2
    else:
      while self.is_finger_pressed() != to_press:
        time.sleep(0.2)
      return to_press

  def is_finger_pressed(self):
    self._send_command('IsPressFinger')
    return self._get_response() == 0

  def delete_position(self, position):
    self._send_command('DeleteID', position)
    self._get_response()

  def delete_all(self):
    self._send_command('DeleteAll')
    self._get_response()

  def verify(self, position):
    self.capture(best_image=False)
    self._send_command('Verify', position)
    self._get_response()

  def identify(self):
    """Identifies finger on scanner against stored enrollment.

    Returns:
      Position of enrollment if identified, otherwise -1.
    """
    try:
      self.capture(best_image=False)
      self._send_command('Identify')
      return self._get_response()
    except FingerprintScannerException as e:
      self.logger.info('Exception: {0}'.format(e))
      return -1

  def capture(self, best_image=False):
    # For enrollment use 'best_image = True'
    # For identification use 'best_image = False'
    if best_image:
      self._send_command('CaptureFinger', True, timeout=10)
    else:
      self._send_command('CaptureFinger', False)
    return self._get_response()

  def get_image(self, raw=False):
    """Captures a fingerprint image (240x216).

    Args:
      raw: if True, capture regardless if finger is placed on sensor.
    Returns:
      A PIL.Image object.
    Raises:
      FingerprintScannerException: if fails to capture image.
    """
    self.capture(best_image=True)
    self._send_command('GetRawImage' if raw else 'GetImage')
    self._get_response()

    data_size = self._IMAGE_SIZE[0] * self._IMAGE_SIZE[1]
    data = self._get_data(data_size, 30)

    return Image.frombytes('L', self._IMAGE_SIZE, data)

  def _send_command(self, command, parameter=0, timeout=None):
    self.logger.debug('Sending command {0}...'.format(command))

    if type(parameter) == bool:
      parameter = 1 if parameter else 0
    command = self._COMMANDS[command]
    packet = bytearray(
        struct.pack(
            FingerprintScanner._CMD_STRUCT,
            FingerprintScanner._PACKETS['Command1'],  # Start code 1
            FingerprintScanner._PACKETS['Command2'],  # Start code 2
            self._device_id,  # Device ID
            parameter,  # Parameter
            command  # Command
        ))
    checksum = sum(packet)
    packet += bytearray(
        struct.pack(FingerprintScanner._CHECKSUM_STRUCT, checksum))

    if timeout is not None:
      self._serial.timeout = timeout
    try:
      sent = self._serial.write(packet)
    finally:
      self._serial.timeout = self._timeout

    self.logger.debug('Sent ({0}).'.format(sent))
    return sent == len(packet)

  def _get_response(self):
    self.logger.debug('Receiving response...')
    packet = bytearray(self._serial.read(12))
    self.logger.debug(
        'Received response: {0}'.format(self._packet_to_string(packet)))

    if not packet:
      raise FingerprintScannerException('Invalid packet to decode.')
    if packet[0] != FingerprintScanner._PACKETS['Command1'] or packet[
        1] != FingerprintScanner._PACKETS['Command2']:
      raise FingerprintScannerException('Invalid command packet to decode.')

    checksum = sum(
        struct.unpack(FingerprintScanner._CHECKSUM_STRUCT,
                      packet[-2:]))  # Last two bytes are checksum
    packet = packet[:-2]
    if sum(packet) != checksum:
      raise FingerprintScannerException('Invalid checksum.')

    packet = struct.unpack(FingerprintScanner._CMD_STRUCT, packet)
    if packet[4] == 0x30:
      return packet[3]
    elif packet[4] == 0x31:
      error = self._ERRORS[packet[3]] if packet[3] in self._ERRORS else packet[
          3]
      raise FingerprintScannerException('Error: {0}'.format(error))
    else:
      raise FingerprintScannerException(
          'Invalid response ({0}).'.format(packet[4]))

  def _send_data(self, data):
    packet = bytearray(
        struct.pack(
            self._DATA_STRUCT(len(data)),
            FingerprintScanner._PACKETS['Data1'],  # Start code 1
            FingerprintScanner._PACKETS['Data2'],  # Start code 2
            self._device_id,  # Device ID
            data  # Data to be sent
        ))
    checksum = sum(packet)
    packet += bytearray(
        struct.pack(FingerprintScanner._CHECKSUM_STRUCT, checksum))

    self.logger.debug('Sending data (size={0})...'.format(len(data)))
    sent = self._serial.write(packet)
    self._serial.flush()
    self.logger.debug('Sent data (size={0}).'.format(sent))
    return sent == len(data)

  def _get_data(self, data_len, timeout=None):
    # Header(2) + ID(2) + data + checksum(2)
    package_size = 1 + 1 + 2 + data_len + 2
    self.logger.debug('Receiving data (size={0})...'.format(package_size))
    if timeout is not None:
      self._serial.timeout = timeout
    try:
      packet = bytearray(self._serial.read(package_size))
    finally:
      self._serial.timeout = self._timeout
    self.logger.debug('Received data (size={0}).'.format(len(packet)))

    if not packet:
      raise FingerprintScannerException('Invaid reponse packet.')

    if packet[0] != FingerprintScanner._PACKETS['Data1'] or packet[
        1] != FingerprintScanner._PACKETS['Data2']:
      raise FingerprintScannerException('Invaid data reponse packet.')

    checksum = sum(
        struct.unpack(FingerprintScanner._CHECKSUM_STRUCT, packet[-2:]))
    packet = packet[:-2]
    if checksum != (sum(packet) & 0xffff):
      raise FingerprintScannerException('Invaid checksum.')

    packet = struct.unpack(self._DATA_STRUCT(data_len), packet)
    return packet[3]

  def _detect_baudrate(self):
    self._serial.timeout = 0.5
    for baudrate in (self._serial.baudrate, ) + self._serial.BAUDRATES:
      if 9600 <= baudrate <= 115200:
        self.logger.debug('Attempting {0}...'.format(baudrate))
        self._serial.baudrate = baudrate
        try:
          self._send_command('Open', True)
          return self._get_response()
        except FingerprintScannerException:
          pass

    raise FingerprintScannerException('Unable to detect baudrate.')

  def _change_baudrate(self, baudrate):
    self.logger.info('Changing baudrate to {0}...'.format(baudrate))
    self._send_command('ChangeBaudrate', baudrate)
    self._get_response()
    self._serial.baudrate = baudrate

  def _packet_to_string(self, packet):
    return ' '.join([hex(x) for x in packet])


class FingerprintScannerException(Exception):
  pass


class FingerprintMonitor(pattern.Worker, pattern.EventEmitter):

  def __init__(self, *args, **kwargs):
    super(FingerprintMonitor, self).__init__(*args, **kwargs)
    self._scanner = FingerprintScanner()
    self._pressed = False
    self.on('pressed', self._on_pressed)

  def _on_start(self):
    self._scanner.initialize()

  def _on_run(self):
    if self._pressed:
      self._pressed = self._scanner.wait_for_finger(
          to_press=False, timeout=datetime.timedelta(seconds=0))
      if self._pressed:
        time.sleep(0.5)
      else:
        self.logger.info('Finger released.')
        self._scanner.set_cmos_led(False)
        self.emit('released')
    else:
      self._scanner.set_cmos_led(True)
      self._pressed = self._scanner.wait_for_finger(
          to_press=True, timeout=datetime.timedelta(seconds=0))
      if self._pressed:
        self.logger.info('Finger pressed.')
        self.emit('pressed')
      else:
        self._scanner.set_cmos_led(False)
        time.sleep(1)

  def _on_pressed(self):
    self.logger.info('Identifying...')
    pos = self._scanner.identify()
    if pos >= 0:
      self.logger.info('Fingerprint identified as {0}'.format(pos))
      self.emit('identified', pos)
    else:
      self.logger.warn('Fingerprint unidentified.')
      self.emit('unidentified')

  def _on_stop(self):
    self._scanner.set_cmos_led(False)
    self._scanner.close()
    self._scanner = None


"""
  def GetTemplate(self, ID):
    if self._send_command('GetTemplate', ID):
      response = self._get_response()
    else:
      raise RuntimeError("Couldn't send packet")
    self.serial.timeout = None  # This is dangerous!
    data = self.getData(498)
    self.serial.timeout = self.timeout
    return [response, data]

  def SetTemplate(self, ID, template):
    if self._send_command('SetTemplate', ID):
      response = self._get_response()
    else:
      raise RuntimeError("Couldn't send packet")
    if self.sendData(template, 498):
      data = self._get_response()
    else:
      raise RuntimeError("Couldn't send packet (data)")
    return [response, data]

  def VerifyTemplate(self, ID, template):
    if self._send_command('VerifyTemplate', ID):
      response = self._get_response()
    else:
      raise RuntimeError("Couldn't send packet")
    if self.sendData(template, 498):
      data = self._get_response()
    else:
      raise RuntimeError("Couldn't send packet (data)")
    return [response, data]

  def IdentifyTemplate(self, template):
    if self._send_command('IdentifyTemplate'):
      response = self._get_response()
    else:
      raise RuntimeError("Couldn't send packet")
    if self.sendData(template, 498):
      data = self._get_response()
    else:
      raise RuntimeError("Couldn't send packet (data)")
    return [response, data]

  def MakeTemplate(self):
    if self._send_command('MakeTemplate'):
      response = self._get_response()
    else:
      raise RuntimeError("Couldn't send packet")
    self.serial.timeout = 10
    data = self.getData(498)
    self.serial.timeout = self.timeout
    return [response, data]

  def SetIAPMode(self):
    if self._send_command('SetIAPMode'):
      return [self._get_response(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def UsbInternalCheck(self):
    self._send_command('UsbInternalCheck')
    self._get_response()

"""
