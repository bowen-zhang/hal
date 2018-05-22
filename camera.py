import datetime
import flask
import io
import picamera
import time

from common import pattern
from common import clocks


class Camera(pattern.Closable):
  def __init__(self,
               clock=clocks.SystemClock(),
               title=None,
               hflip=False,
               vflip=False,
               rotation=0,
               *args,
               **kwargs):
    super(Camera, self).__init__(self, *args, **kwargs)

    self._clock = clock
    self._title = title
    self._recording = False

    self._camera = picamera.PiCamera()
    self._camera.hflip = hflip
    self._camera.vflip = vflip
    self._camera.rotation = rotation
    self._camera.resolution = (1920, 1080)
    self._camera.framerate = 15
    self._camera.annotate_text_size = 20
    self._camera.annotate_background = picamera.color.Color('#000000')

  @property
  def camera(self):
    return self._camera

  def capture(self, filepath):
    self.logger.debug('Capture image (%s)', filepath)
    self.update_annotation()
    self._camera.capture(filepath, format='jpeg', thumbnail=None)

  def update_annotation(self):
    now = self._clock.utc
    self._camera.annotate_text = '{0} - {1: %b %d, %Y - %H:%M:%S}'.format(
        self._title, now)

  def close(self):
    if self._camera:
      self._camera.close()
      self._camera = None
    super(Camera, self).close()


class Recorder(pattern.Worker):
  def __init__(self, camera, file_path='.', *args, **kwargs):
    """
    Args:
      camera: a Camera instance.
      file_path: directory to save recordings.
    """
    super(Recorder, self).__init__(self, *args, **kwargs)

    self._camera = camera
    self._file_path = file_path
    self._recording = False

  def _on_start(self):
    self.logger.debug('Start recording...')
    self._camera.camera.start_recording(
        self._file_path, format='h264', resize=(640, 480), bitrate=1000000)
    self._recording = True

  def _on_run(self):
    self._camera.update_annotation()
    time.sleep(1)

  def _on_stop(self):
    self.logger.debug('Stop recording...')
    self._camera.camera.stop_recording()
    self._recording = False


class Streamer(pattern.Worker):
  TIMEOUT = datetime.timedelta(seconds=10)

  def __init__(self,
               web,
               camera,
               width=640,
               height=480,
               quality=85,
               frame_rate=2,
               *args,
               **kwargs):
    super(Streamer, self).__init__(*args, **kwargs)

    web.add_url_rule('/video', view_func=self._on_video_request)
    self._width = width
    self._height = height
    self._quality = quality
    self._min_interval = 1.0 / frame_rate
    self._camera = camera
    self._frame = None
    self._expiration = datetime.datetime.now()

  @property
  def frame(self):
    self._renew()

    while not self._frame:
      time.sleep(0)

    return self._frame

  def _renew(self):
    self._expiration = datetime.datetime.now() + Streamer.TIMEOUT
    if not self.is_running:
      self.start()

  def _on_start(self):
    self.logger.debug('Starting streaming...')
    self._stream = io.BytesIO()

  def _on_run(self):
    if datetime.datetime.now() > self._expiration:
      return False

    start = time.time()
    self._camera.camera.capture(
        self._stream,
        format='jpeg',
        use_video_port=True,
        resize=(self._width, self._height),
        quality=self._quality,
        thumbnail=None)
    self._stream.seek(0)
    self._frame = (self._stream.read(), start)
    self._stream.seek(0)
    self._stream.truncate()
    end = time.time()
    delay = self._min_interval - (end - start)
    if delay > 0:
      time.sleep(delay)

  def _on_stop(self):
    self._stream.close()
    self.logger.debug('Stopped streaming.')

  def _on_video_request(self):
    return flask.Response(
        self._stream_video(),
        mimetype='multipart/x-mixed-replace; boundary=frame')

  def _stream_video(self):
    last_timestamp = None
    data, timestamp = self.frame
    while self.is_running:
      while self.is_running and timestamp == last_timestamp:
        time.sleep(0.1)
        data, timestamp = self.frame
      last_timestamp = timestamp

      yield (b'--frame\r\n'
             b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n')
