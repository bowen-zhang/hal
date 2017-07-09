import picamera
import time

from common import pattern


class Camera(pattern.Worker):

    def __init__(self, clock, *args, **kwargs):
        super(Camera, self).__init__(self, *args, **kwargs)

        self._clock = clock
        self._title = 'Forward'
        self._recording = False

        self._camera = picamera.PiCamera()
        self._camera.resolution = (640, 480)
        self._camera.framerate = 15
        self._camera.annotate_text_size = 20
        self._camera.annotate_background = picamera.color.Color('#000000')

    @property
    def recording(self):
        return self._recording

    def start_recording(self, filepath):
        self._filepath = filepath
        self.start()

    def stop_recording(self):
        self.stop()

    def capture(self, filepath):
        self.logger.debug('Capture image (%s)', filepath)
        self._camera.capture(filepath, format='jpeg', use_video_port=True)

    def close(self):
        if self._camera:
            self._camera.close()
            self._camera = None
        super(Camera, self).close()

    def _on_start(self):
        self.logger.debug('Start recording...')
        self._camera.start_recording(self._filepath, format='h264', bitrate=1000000)
        self._recording = True

    def _on_run(self):
        now = self._clock.utc
        self._camera.annotate_text = '{0} - {1: %b %d, %Y - %H:%M:%S}'.format(self._title, now)
        time.sleep(1)

    def _on_stop(self):
        self.logger.debug('Stop recording...')
        self._camera.stop_recording()
        self._recording = False
