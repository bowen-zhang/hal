from hal import relay


def test_relay():
  switch = relay.RelaySwitch(pin=18)
  switch.toggle()


if __name__ == '__main__':
  test_relay()
