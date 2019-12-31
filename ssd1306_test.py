import time
from . import ssd1306


def test():
  display = ssd1306.Display()
  display.text(0, 0, 'Hello World!')
  display.text(10, 20, 'Bowen Zhang')
  display.rectangle(120, 0, 127, 10)
  time.sleep(5)


if __name__ == '__main__':
  test()
