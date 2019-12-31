from . import chromecast


def test():
  cast = chromecast.Chromecast(host='192.168.86.209')
  cast.wait()
  cast.set_volume(0.4)
  mediacontroller = cast.media_controller
  mediacontroller.play_media(
      'http://192.168.86.4:8080/audio/c80ca8a344b0cd2e8660d46842f76b0e.wav',
      'audio/wav')


if __name__ == '__main__':
  test()