import smbus


def is_i2c_available(address):
  bus = smbus.SMBus(1)
  try:
    bus.read_byte(address)
    return True
  except:
    return False
