'''
MFRC522 to Raspberry Pi Connection:
  SDA   ->    GPIO08/SPI_CE0_N (24)
  SCK   ->    GPIO11/SPI_CLK (23)
  MOSI  ->    GPIO10/SPI_MOSI (19)
  MISO  ->    GPIO09/SPI_MISO (21)
  GND   ->    Ground (20)
  RST   ->    GPIO25/GPIO_GEN6 (22)
  3.3V  ->    3.3v (17)
'''

import RPi.GPIO as GPIO
import spi
import signal
import time

from common import pattern

_NRSTPD = 22

_MAX_LEN = 16

_PCD_IDLE = 0x00
_PCD_AUTHENT = 0x0E
_PCD_RECEIVE = 0x08
_PCD_TRANSMIT = 0x04
_PCD_TRANSCEIVE = 0x0C
_PCD_RESETPHASE = 0x0F
_PCD_CALCCRC = 0x03

_PICC_REQIDL = 0x26
_PICC_REQALL = 0x52
_PICC_ANTICOLL = 0x93
_PICC_SElECTTAG = 0x93
_PICC_AUTHENT1A = 0x60
_PICC_AUTHENT1B = 0x61
_PICC_read_spi = 0x30
_PICC_write_spi = 0xA0
_PICC_DECREMENT = 0xC0
_PICC_INCREMENT = 0xC1
_PICC_RESTORE = 0xC2
_PICC_TRANSFER = 0xB0
_PICC_HALT = 0x50

_MI_OK = 0
_MI_NOTAGERR = 1
_MI_ERR = 2

Reserved00 = 0x00
CommandReg = 0x01
CommIEnReg = 0x02
DivlEnReg = 0x03
CommIrqReg = 0x04
DivIrqReg = 0x05
ErrorReg = 0x06
Status1Reg = 0x07
Status2Reg = 0x08
FIFODataReg = 0x09
FIFOLevelReg = 0x0A
WaterLevelReg = 0x0B
ControlReg = 0x0C
BitFramingReg = 0x0D
CollReg = 0x0E
Reserved01 = 0x0F

Reserved10 = 0x10
ModeReg = 0x11
TxModeReg = 0x12
RxModeReg = 0x13
TxControlReg = 0x14
TxAutoReg = 0x15
TxSelReg = 0x16
RxSelReg = 0x17
RxThresholdReg = 0x18
DemodReg = 0x19
Reserved11 = 0x1A
Reserved12 = 0x1B
MifareReg = 0x1C
Reserved13 = 0x1D
Reserved14 = 0x1E
SerialSpeedReg = 0x1F

Reserved20 = 0x20
CRCResultRegM = 0x21
CRCResultRegL = 0x22
Reserved21 = 0x23
ModWidthReg = 0x24
Reserved22 = 0x25
RFCfgReg = 0x26
GsNReg = 0x27
CWGsPReg = 0x28
ModGsPReg = 0x29
TModeReg = 0x2A
TPrescalerReg = 0x2B
TReloadRegH = 0x2C
TReloadRegL = 0x2D
TCounterValueRegH = 0x2E
TCounterValueRegL = 0x2F

Reserved30 = 0x30
TestSel1Reg = 0x31
TestSel2Reg = 0x32
TestPinEnReg = 0x33
TestPinValueReg = 0x34
TestBusReg = 0x35
AutoTestReg = 0x36
VersionReg = 0x37
AnalogTestReg = 0x38
TestDAC1Reg = 0x39
TestDAC2Reg = 0x3A
TestADCReg = 0x3B
Reserved31 = 0x3C
Reserved32 = 0x3D
Reserved33 = 0x3E
Reserved34 = 0x3F


class RFIDController(pattern.Singleton):

  def __init__(self, dev='/dev/spidev0.0', spd=1000000, *args, **kwargs):
    super(RFIDController, self).__init__(*args, **kwargs)

    spi.openSPI(device=dev, speed=spd)
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(22, GPIO.OUT)
    self._initialize()

  def _initialize(self):
    GPIO.output(_NRSTPD, 1)

    self._reset()

    self._write_spi(TModeReg, 0x8D)
    self._write_spi(TPrescalerReg, 0x3E)
    self._write_spi(TReloadRegL, 30)
    self._write_spi(TReloadRegH, 0)

    self._write_spi(TxAutoReg, 0x40)
    self._write_spi(ModeReg, 0x3D)
    self._antenna_on()

  def _reset(self):
    self._write_spi(CommandReg, _PCD_RESETPHASE)

  def _write_spi(self, addr, val):
    spi.transfer(((addr << 1) & 0x7E, val))

  def _read_spi(self, addr):
    val = spi.transfer((((addr << 1) & 0x7E) | 0x80, 0))
    return val[1]

  def _get_bit_mask(self, reg, mask):
    return self._read_spi(reg) & mask

  def _set_bit_mask(self, reg, mask):
    tmp = self._read_spi(reg)
    self._write_spi(reg, tmp | mask)

  def _clear_bit_mask(self, reg, mask):
    tmp = self._read_spi(reg)
    self._write_spi(reg, tmp & (~mask))

  def _antenna_on(self):
    temp = self._read_spi(TxControlReg)
    if (~(temp & 0x03)):
      self._set_bit_mask(TxControlReg, 0x03)

  def _antenna_off(self):
    self._clear_bit_mask(TxControlReg, 0x03)

  def send(self, command, data):
    irqEn = 0x00
    waitIRq = 0x00

    if command == _PCD_AUTHENT:
      irqEn = 0x12
      waitIRq = 0x10
    if command == _PCD_TRANSCEIVE:
      irqEn = 0x77
      waitIRq = 0x30

    self._write_spi(CommIEnReg, irqEn | 0x80)
    self._clear_bit_mask(CommIrqReg, 0x80)
    self._set_bit_mask(FIFOLevelReg, 0x80)

    self._write_spi(CommandReg, _PCD_IDLE)

    for b in data:
      self._write_spi(FIFODataReg, b)

    self._write_spi(CommandReg, command)

    if command == _PCD_TRANSCEIVE:
      self._set_bit_mask(BitFramingReg, 0x80)

    i = 2000
    n = 0
    while True:  #i != 0 and (n&0x01) == 0 and (n&waitIRq) == 0:
      n = self._read_spi(CommIrqReg)
      i -= 1
      if ~((i != 0) and ~(n & 0x01) and ~(n & waitIRq)):
        break

    self._clear_bit_mask(BitFramingReg, 0x80)

    if i == 0:
      return (_MI_ERR, None, None)

    if (self._read_spi(ErrorReg) & 0x1B) != 0x00:
      return (_MI_ERR, None, None)

    status = _MI_OK
    if n & irqEn & 0x01:
      status = _MI_NOTAGERR

    if command != _PCD_TRANSCEIVE:
      return (status, None, None)

    n = self._read_spi(FIFOLevelReg)
    lastBits = self._read_spi(ControlReg) & 0x07
    if lastBits != 0:
      bits = (n - 1) * 8 + lastBits
    else:
      bits = n * 8

    if n == 0:
      n = 1
    if n > _MAX_LEN:
      n = _MAX_LEN

    response = []
    for i in range(n):
      response.append(self._read_spi(FIFODataReg))

    return (status, response, bits)

  def detect(self):
    try:
      self._request(_PICC_REQIDL)
    except MFRC522Exception as e:
      return None

    uid = self._get_uid()
    return RFIDCard(self, uid)

  def ensure(self, status, size=None, expected_size=None, msg='Error'):
    if status != _MI_OK:
      raise MFRC522Exception('{0}: status={1}'.format(msg, status))
    if size is not None and expected_size is not None and size != expected_size:
      raise MFRC522Exception('{0}: response size={1}'.format(msg, size))

  def calculate_crc(self, data):
    self._clear_bit_mask(DivIrqReg, 0x04)
    self._set_bit_mask(FIFOLevelReg, 0x80)
    for b in data:
      self._write_spi(FIFODataReg, b)
    self._write_spi(CommandReg, _PCD_CALCCRC)

    i = 0xFF
    n = 0
    while i > 0 and not (n & 0x04):
      n = self._read_spi(DivIrqReg)
      i = i - 1

    return [
        self._read_spi(CRCResultRegL),
        self._read_spi(CRCResultRegM),
    ]

  def has_cryptol(self):
    return self._get_bit_mask(Status2Reg, 0x08) != 0

  def stop_cryptol(self):
    self._clear_bit_mask(Status2Reg, 0x08)

  def _request(self, mode):
    self._write_spi(BitFramingReg, 0x07)

    tag_type = [mode]
    (status, response, bits) = self.send(_PCD_TRANSCEIVE, tag_type)
    self.ensure(status, bits, 0x10, 'Failed to request')

    return response

  def _get_uid(self):
    self._write_spi(BitFramingReg, 0x00)

    cmd_data = [_PICC_ANTICOLL, 0x20]
    (status, response, bits) = self.send(_PCD_TRANSCEIVE, cmd_data)
    self.ensure(status, bits, 40, 'Failed to get uid')

    uid_check = response[0] ^ response[1] ^ response[2] ^ response[3]
    if uid_check != response[4]:
      raise MFRC522Exception('Failed to get uid: uid check failed.')

    return response


class RFIDReader(pattern.Worker, pattern.EventEmitter):

  def __init__(self, controller, *args, **kwargs):
    super(RFIDReader, self).__init__(*args, **kwargs)
    self._controller = controller
    self._last_uid = None
    self.start()

  def _on_run(self):
    card = self._controller.detect()
    if card:
      if not self._last_uid:
        # detected a card
        self.logger.debug('<no card> => <%s>', card.uid)
        self._last_uid = card.uid
        self.emit('card', card)
        self._controller.stop_cryptol()
      elif card.uid != self._last_uid:
        # detected a different card
        self.logger.debug('<%s> => <%s>', self._last_uid, card.uid)
        self._last_uid = card.uid
        self.emit('card', card)
        self._controller.stop_cryptol()
      else:
        # still the same card
        time.sleep(0.3)
    else:
      if self._last_uid:
        # card is removed
        self.logger.debug('<%s> => <no card>', self._last_uid)
        self._last_uid = None
        time.sleep(3)
      else:
        # still no card
        time.sleep(0.3)


class RFIDCard(object):

  def __init__(self, controller, raw_uid):
    self._controller = controller
    self._raw_uid = raw_uid
    self._uid = raw_uid[0:4]

    # This is the default key for authentication
    self._key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

  @property
  def uid(self):
    return self._to_int32(self._uid)

  def authenticate(self, block, mode=_PICC_AUTHENT1A):
    """
      Args:
        mode: A or B.
        block: index of block to authenticate.
        key: key for the sector of specified block.
        uid: uid of card.
    """
    buff = [mode, block] + self._key + self._uid

    # Now we start the authentication itself
    (status, response, bits) = self._controller.send(_PCD_AUTHENT, buff)
    self._controller.ensure(status, msg='Failed to authenticate')

    if not self._controller.has_cryptol():
      raise MFRC522Exception('Authentication error: cryptol is not set.')

  def select_tag(self):
    cmd_data = [_PICC_SElECTTAG, 0x70] + self._raw_uid
    crc = self._controller.calculate_crc(cmd_data)
    cmd_data += crc
    (status, response, bits) = self._controller.send(_PCD_TRANSCEIVE, cmd_data)
    self._controller.ensure(status, bits, 0x18, 'Failed to select tag')

    return response[0]

  def read_str(self, block):
    data = self.read(block)
    return ''.join([chr(x) for x in data]).strip('\0')

  def read_int32(self, block, offset):
    assert 0 <= offset and offset <= 12
    data = self.read(block)
    return self._to_int32(data[offset:offset + 4])

  def read(self, block):
    assert 0 <= block and block < 64

    cmd_data = [_PICC_read_spi, block]
    crc = self._controller.calculate_crc(cmd_data)
    cmd_data += crc
    (status, response, bits) = self._controller.send(_PCD_TRANSCEIVE, cmd_data)
    self._controller.ensure(status, len(response), 16, 'Failed to read')

    return response

  def write_str(self, block, value):
    assert len(value) <= 16
    data = [ord(x) for x in value]
    while len(data) < 16:
      data.append(0)
    self.write(block, data)

  def write_int32(self, block, offset, value):
    assert 0 <= offset and offset <= 12
    data = self.read(block)
    data[offset] = value >> 24
    data[offset + 1] = (value >> 16) & 0xFF
    data[offset + 2] = (value >> 8) & 0xFF
    data[offset + 3] = value & 0xFF
    self.write(block, data)

  def write(self, block, data):
    assert 0 <= block and block < 64
    assert len(data) == 16

    cmd_data = [_PICC_write_spi, block]
    crc = self._controller.calculate_crc(cmd_data)
    cmd_data += crc
    (status, response, bits) = self._controller.send(_PCD_TRANSCEIVE, cmd_data)
    self._controller.ensure(status, bits, 4, 'Failed to write')
    if (response[0] & 0x0F) != 0x0A:
      raise MFRC522Exception('Failed to write: response={0}'.format(response))

    cmd_data = data
    crc = self._controller.calculate_crc(cmd_data)
    cmd_data += crc
    (status, response, size) = self._controller.send(_PCD_TRANSCEIVE, cmd_data)
    self._controller.ensure(status, bits, 4, 'Failed to write')
    if (response[0] & 0x0F) != 0x0A:
      raise MFRC522Exception('Failed to write: response={0}'.format(response))

  def dump(self):
    for i in range(0, 64):
      try:
        self.authenticate(block=i, mode=_PICC_AUTHENT1A)
        data = self.read(i)
        print('Sector {0}: {1}'.format(i, data))
      except MFRC522Exception as e:
        print(str(e))

  def _to_int32(self, data):
    return data[0] << 24 | data[1] << 16 | data[2] << 8 | data[3]


class MFRC522Exception(Exception):
  pass
