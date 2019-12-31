import logging
import sys
import time
import wave

from hal import audio
from common import audio as audio_util

file = None


def test_audio():
  devices = audio.get_all_devices()
  for i, device in enumerate(devices):
    print('--------------------')
    print('device {0}: {1}'.format(i, device['name']))
    print(device)
    print()

  global file
  file = wave.open('test.wav', 'wb')
  file.setnchannels(1)
  file.setsampwidth(2)
  file.setframerate(44100)
  file.setnframes(0)

  a = audio.Audio(name='C-Media USB Headphone Set.*', sample_rate=44100)
  #a = audio.Audio(name='USB Audio Device', sample_rate=44100)
  a.on('sample', _on_sample)
  time.sleep(10)
  a.stop()

  file.close()


def _on_sample(a, data):
  power = audio_util.create_power_spectrum(data)
  step = len(power) / 10
  power = power[::step]
  sys.stdout.write('\r' + ','.join([str(int(x)) for x in power]))
  sys.stdout.flush()

  file.writeframes(data)


if __name__ == '__main__':
  logging.basicConfig()
  test_audio()
