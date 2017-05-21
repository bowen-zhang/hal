"""
Enable serial port
Disable serial console
"""
"""Communication with the Fingerprint Scanner using R-Pi"""
from PIL import Image
import os, sys
import serial
import struct
import time

comm_struct = lambda: '<BBHIH'
data_struct = lambda x: '<BBH' + str(x) + 's'
checksum_struct = lambda: '<H'

packets = {
    'Command1': 0x55,
    'Command2': 0xAA,
    'Data1': 0x5A,
    'Data2': 0xA5,
    '\x55\xAA': 'C',
    '\x5A\xA5': 'D'
}

commands = {
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
    'GetRawImage': 0x63,  # Capture & Download raw fingerprint image (32'\x240)
    'GetTemplate': 0x70,  # Download the template of the specified ID
    'SetTemplate': 0x71,  # Upload the template of the specified ID
    'GetDatabaseStart': 0x72,  # Start database download, obsolete
    'GetDatabaseEnd': 0x73,  # End database download, obsolete
    'UpgradeFirmware': 0x80,  # Not supported
    'UpgradeISOCDImage': 0x81,  # Not supported
    'Ack': 0x30,  # Acknowledge
    'Nack': 0x31  # Non-acknowledge
}

errors = {
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

responses = {'Ack': 0x30, 'Nack': 0x31, 0x30: 'Ack', 0x31: 'Nack'}


def encode_command_packet(command=None, parameter=0, device_id=1):

  command = commands[command]
  packet = bytearray(
      struct.pack(
          comm_struct(),
          packets['Command1'],  # Start code 1
          packets['Command2'],  # Start code 2
          device_id,  # Device ID
          parameter,  # Parameter
          command  # Command
      ))
  checksum = sum(packet)
  packet += bytearray(struct.pack(checksum_struct(), checksum))
  return packet


def encode_data_packet(data=None, data_len=0, device_id=1):

  packet = bytearray(
      struct.pack(
          data_struct(data_len),
          packets['Data1'],  # Start code 1
          packets['Data2'],  # Start code 2
          device_id,  # Device ID
          data  # Data to be sent
      ))
  checksum = sum(packet)
  packet += bytearray(struct.pack(checksum_struct(), checksum))
  return packet


def decode_command_packet(packet):
  response = {
      'Header': None,
      'DeviceID': None,
      'ACK': None,
      'Parameter': None,
      'Checksum': None
  }
  _debug = packet
  if packet == '':  # Nothing to decode
    response['ACK'] = False
    return response
  # Check if it is a data packet:
  if packet[0] == packets['Data1'] and packet[1] == packets['Data2']:
    return decode_data_packet(packet)
  # Strip the checksum and get the values out
  checksum = sum(struct.unpack(checksum_struct(),
                               packet[-2:]))  # Last two bytes are checksum
  packet = packet[:-2]
  response['Checksum'] = sum(packet) == checksum  # True if checksum is correct

  try:
    packet = struct.unpack(comm_struct(), packet)
  except Exception as e:
    raise Exception(str(e) + ' ' + str(packet[0]))
  response['Header'] = hex(packet[0])[2:] + hex(packet[1])[2:]
  response['DeviceID'] = hex(packet[2])[2:]
  response['ACK'] = packet[4] != 0x31  # Not NACK, might be command
  # response['Parameter'] = packet[3] if response['ACK'] else errors[packet[3]]
  response['Parameter'] = errors[packet[3]] if (
      not response['ACK'] and packet[3] in errors) else packet[3]

  print response
  return response


def decode_data_packet(packet):
  response = {'Header': None, 'DeviceID': None, 'Data': None, 'Checksum': None}
  if packet == '':
    response['ACK'] = False
    return response
  # Check if it is a command packet:
  if packet[0] == packets['Command1'] and packet[1] == packets['Command2']:
    return decode_command_packet(packet)

  # Strip the checksum and get the values out
  checksum = sum(struct.unpack(checksum_struct(),
                               packet[-2:]))  # Last two bytes are checksum
  packet = packet[:-2]
  # Data sum might be larger than the checksum field:
  chk = sum(packet)
  chk &= 0xffff
  response['Checksum'] = chk == checksum  # True if checksum is correct

  data_len = len(packet) - 4  # Exclude the header (2) and device ID (2)

  packet = struct.unpack(data_struct(data_len), packet)
  response['Header'] = hex(packet[0])[2:] + hex(packet[1])[2:]
  response['DeviceID'] = hex(packet[2])[2:]
  response['Data'] = packet[3]
  # print packet
  return response


class FingerPi():

  def __init__(self,
               port='/dev/ttyS0',
               baudrate=9600,
               device_id=0x01,
               timeout=2,
               *args,
               **kwargs):
    self.port = port
    self.baudrate = baudrate
    if not os.path.exists(port):
      raise IOError("Port " + self.port + " cannot be opened!")

    self.serial = serial.Serial(
        port=self.port,
        baudrate=self.baudrate,
        timeout=timeout,
        *args,
        **kwargs)
    print 'Created serial port.'

    self.device_id = device_id
    self.timeout = 5

    self.save = False

    self.serial.flushInput()
    self.serial.flushOutput()

  ##########################################################
  ## Send/Get routines

  def sendCommand(self, command, parameter=0x00):
    if type(parameter) == bool:
      parameter = parameter * 1
    packet = encode_command_packet(
        command, parameter, device_id=self.device_id)

    # The length of the written command should match:
    print 'Sending command {0}...'.format(command)
    result = len(packet) == self.serial.write(packet)
    #self.serial.flush()
    print 'Result: {0}'.format(result)
    return result

  def getResponse(self, response_len=12):
    print 'Getting response...'
    response = self.serial.read(response_len)
    print 'Received response.'
    return decode_command_packet(bytearray(response))

  def sendData(self, data, data_len):
    packet = encode_data_packet(data, data_len, device_id=self.device_id)
    result = len(packet) == self.serial.write(packet)
    self.serial.flush()
    return result

  def getData(self, data_len):
    # Data length is different for every command
    response = self.serial.read(
        1 + 1 + 2 + data_len + 2)  # Header(2) + ID(2) + data + checksum(2)
    # return response
    return decode_data_packet(bytearray(response))

  ##########################################################
  ## Send/Get routines
  def Open(self, extra_info=False, check_baudrate=False):
    print 'Opening...'
    # Check baudrate:
    if check_baudrate:
      self.serial.timeout = 0.5
      for baudrate in (self.serial.baudrate, ) + self.serial.BAUDRATES:
        if 9600 <= baudrate <= 115200:
          print 'Attempting {0}...'.format(baudrate)
          self.serial.baudrate = baudrate
          if not self.sendCommand('Open', extra_info):
            raise RuntimeError("Couldn't send 'Open' packet!")
          # print baudrate
          response = self.getResponse()
          if response['ACK']:
            # Decoded something
            response['Parameter'] = baudrate
            break

      if self.serial.baudrate > 115200:  # Cannot be more than that
        raise RuntimeError("Couldn't find appropriate baud rate!")
    else:
      self.sendCommand('Open', extra_info)
      response = self.getResponse()
    data = None
    if extra_info:
      data = self.getData(16 + 4 + 4)
    self.serial.timeout = self.timeout
    return [response, data]

  def Close(self):
    self.ChangeBaudrate(9600)
    if self.sendCommand('Close'):
      response = self.getResponse()
      self.serial.flushInput()
      self.serial.flushOutput()
      self.serial.close()
      return [response, None]

    else:
      raise RuntimeError("Couldn't send packet")

  def UsbInternalCheck(self):
    if self.sendCommand('UsbInternalCheck'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def CmosLed(self, on=False):
    if self.sendCommand('CmosLed', on):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def ChangeBaudrate(self, baudrate):
    if self.sendCommand('ChangeBaudrate', baudrate):
      response = self.getResponse()
      self.serial.baudrate = baudrate
      return [response, None]
    else:
      raise RuntimeError("Couldn't send packet")

  def GetEnrollCount(self):
    if self.sendCommand('GetEnrollCount'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def CheckEnrolled(self, ID):
    if self.sendCommand('CheckEnrolled', ID):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def EnrollStart(self, ID):
    self.save = ID == -1
    if self.sendCommand('EnrollStart', ID):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def Enroll1(self):
    if self.sendCommand('Enroll1'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def Enroll2(self):
    if self.sendCommand('Enroll2'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def Enroll3(self):
    if self.sendCommand('GetEnrollCount'):
      response = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet")
    data = None
    if self.save:
      data = self.getData(498)
    return [response, data]

  def IsPressFinger(self):
    if self.sendCommand('IsPressFinger'):
      resp = self.getResponse()
      return resp['Parameter'] == 0
    else:
      raise RuntimeError("Couldn't send packet")

  def DeleteId(self, ID):
    if self.sendCommand('DeleteId', ID):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def DeleteAll(self):
    if self.sendCommand('DeleteAll'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def Verify(self, ID):
    if self.sendCommand('Verify'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def Identify(self):
    if self.sendCommand('Identify'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def VerifyTemplate(self, ID, template):
    if self.sendCommand('VerifyTemplate', ID):
      response = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet")
    if self.sendData(template, 498):
      data = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet (data)")
    return [response, data]

  def IdentifyTemplate(self, template):
    if self.sendCommand('IdentifyTemplate'):
      response = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet")
    if self.sendData(template, 498):
      data = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet (data)")
    return [response, data]

  def CaptureFinger(self, best_image=False):
    # For enrollment use 'best_image = True'
    # For identification use 'best_image = False'
    if best_image:
      self.serial.timeout = 10
    if self.sendCommand('CaptureFinger', best_image):
      self.serial.timeout = self.timeout
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def MakeTemplate(self):
    if self.sendCommand('MakeTemplate'):
      response = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet")
    self.serial.timeout = 10
    data = self.getData(498)
    self.serial.timeout = self.timeout
    return [response, data]

  def GetImage(self, dim=(240, 216)):
    # The documentation is ambiguous:
    # Dimensions could be 202x258 or 256x256
    to_read = dim[0] * dim[1]

    if self.sendCommand('GetImage'):
      response = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet")
    data = None
    if response['ACK']:
      self.serial.timeout = None  # This is dangerous!
      data = self.getData(dim[0] * dim[1])
      self.serial.timeout = self.timeout
    return [response, data]

  def GetRawImage(self, dim=(160, 120)):
    if self.sendCommand('GetRawImage'):
      response = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet")
    data = None
    if response['ACK']:
      self.serial.timeout = None  # This is dangerous!
      data = self.getData(dim[0] * dim[1])
      self.serial.timeout = self.timeout
      # Add dimensions to the data
      data['Data'] = (data['Data'], dim)
    return [response, data]

  def GetTemplate(self, ID):
    if self.sendCommand('GetTemplate', ID):
      response = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet")
    self.serial.timeout = None  # This is dangerous!
    data = self.getData(498)
    self.serial.timeout = self.timeout
    return [response, data]

  def SetTemplate(self, ID, template):
    if self.sendCommand('SetTemplate', ID):
      response = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet")
    if self.sendData(template, 498):
      data = self.getResponse()
    else:
      raise RuntimeError("Couldn't send packet (data)")
    return [response, data]

  def GetDatabaseStart(self):
    if self.sendCommand('GetDatabaseStart'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def GetDatabaseEnd(self):
    if self.sendCommand('GetDatabaseEnd'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")

  def SetIAPMode(self):
    if self.sendCommand('SetIAPMode'):
      return [self.getResponse(), None]
    else:
      raise RuntimeError("Couldn't send packet")


if __name__ == '__main__':
  f = FingerPi()
  f.Open(extra_info=True, check_baudrate=True)
  f.ChangeBaudrate(115200)
  try:
    f.CmosLed(True)
    print 'Place finger on scanner...'
    while not f.IsPressFinger():
      time.sleep(0.5)
    f.CaptureFinger(True)
    resp = f.GetImage()
    img = Image.frombytes('L', (240, 216), resp[1]['Data'])
    img.save('1.png')
    print 'Captured.'
  finally:
    f.CmosLed(False)
    f.Close()
