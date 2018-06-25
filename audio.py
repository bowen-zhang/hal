import datetime
import pyaudio
import re
import wave

from common import audio as audio_util
from common import pattern


def get_all_devices():
  audio = pyaudio.PyAudio()
  count = audio.get_device_count()
  return [audio.get_device_info_by_index(i) for i in range(count)]


class Audio(pattern.Worker, pattern.EventEmitter):

  SAMPLE_SECONDS = 1
  FORMAT = pyaudio.paInt16

  def __init__(self, name, sample_rate, *args, **kwargs):
    super(Audio, self).__init__(
        worker_name='Audio - {0}'.format(name), *args, **kwargs)

    self._audio = None
    self._stream = None
    self._sample_rate = sample_rate
    self._buffer_size = sample_rate * Audio.SAMPLE_SECONDS
    self._device_info = self._find_device(name)

    self.start()

  def _on_start(self):
    self._audio = pyaudio.PyAudio()
    self._stream = self._audio.open(
        format=Audio.FORMAT,
        input=True,
        channels=1,
        rate=self._sample_rate,
        input_device_index=self._device_info['index'],
        frames_per_buffer=self._buffer_size)

  def _on_run(self):
    data = self._stream.read(self._buffer_size)
    self.emit('sample', self, data)
    if self.emittable('spectrum'):
      spectrum = audio_util.create_power_spectrum(data)
      self.emit('spectrum', self, spectrum)

  def _on_stop(self):
    self._stream.stop_stream()
    self._stream.close()
    self._audio.terminate()

  def _find_device(self, name):
    devices = get_all_devices()
    device = [x for x in devices if re.match(name, x['name'])]
    if not device:
      raise AudioException('Device \"{0}\" not found.'.format(name))

    return device[0]


class AudioFromFile(pattern.Worker, pattern.EventEmitter):

  _ONE_SECOND = datetime.timedelta(seconds=1)

  def __init__(self, path, clock, *args, **kwargs):
    super(AudioFromFile, self).__init__(
        worker_name='AudioFromFile', *args, **kwargs)
    self._path = path
    self._clock = clock
    self._timestamp = datetime.timedelta(seconds=0)

    self.start()

  @property
  def timestamp(self):
    return self._timestamp

  def _on_start(self):
    self._file = wave.open(self._path, 'rb')
    self._frames_per_sec = self._file.getnchannels() * self._file.getframerate(
    )
    self._nframes = self._file.getnframes()
    self._start_time = self._clock.utc
    self._timestamp = datetime.timedelta(seconds=0)

  def _on_run(self):
    if self._nframes <= 0:
      self.logger.debug('Reached end of audio file.')
      self.emit('end', self)
      return False

    if self._clock.utc < self._start_time + self._timestamp:
      return

    frames = self._file.readframes(self._frames_per_sec)
    self._nframes -= self._frames_per_sec
    self.emit('sample', self, frames)
    self._timestamp += AudioFromFile._ONE_SECOND

  def _on_stop(self):
    if self._file:
      self._file.close()
      self._file = None


class AudioException(Exception):
  pass
