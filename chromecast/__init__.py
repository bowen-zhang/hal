import collections
import enum
import error
import requests
import socket_client
import threading
import types
import uuid


class DeviceMetadata(object):
  def __init__(self, friendly_name, model_name, manufacturer, uuid, cast_type):
    self._friendly_name = friendly_name
    self._model_name = model_name
    self._manufacturer = manufacturer
    self._uuid = uuid
    self._cast_type = cast_type

  @property
  def friendly_name(self):
    return self._friendly_name

  @property
  def cast_type(self):
    return self._cast_type

  @staticmethod
  def create_from_host(host):
    session = requests.Session()
    session.headers['content-type'] = 'application/json'
    try:
      req = session.get(
          'http://{0}:8008/setup/eureka_info?options=detail'.format(host),
          timeout=10)

      req.raise_for_status()

      # The Requests library will fall back to guessing the encoding in case
      # no encoding is specified in the response headers - which is the case
      # for the Chromecast.
      # The standard mandates utf-8 encoding, let's fall back to that instead
      # if no encoding is provided, since the autodetection does not always
      # provide correct results.
      if req.encoding is None:
        req.encoding = 'utf-8'

      status = req.json()

      friendly_name = status.get('name', "Unknown Chromecast")
      model_name = "Unknown model name"
      manufacturer = "Unknown manufacturer"
      if 'detail' in status:
        model_name = status['detail'].get('model_name', model_name)
        manufacturer = status['detail'].get('manufacturer', manufacturer)

      udn = status.get('ssdp_udn', None)
      device_uuid = uuid.UUID(udn.replace('-', '')) if udn else None
      cast_type = types.CAST_TYPE_MAPPING.get(model_name.lower(),
                                              types.CastType.CHROMECAST)

      return DeviceMetadata(friendly_name, model_name, manufacturer,
                            device_uuid, cast_type)

    except (requests.exceptions.RequestException, ValueError):
      return None


class Chromecast(object):
  """
    Class to interface with a ChromeCast.

    :param port: The port to use when connecting to the device, set to None to
                 use the default of 8009. Special devices such as Cast Groups
                 may return a different port number so we need to use that.
    :param device: DeviceStatus with initial information for the device.
    :type device: pychromecast.dial.DeviceStatus
    :param tries: Number of retries to perform if the connection fails.
                  None for inifinite retries.
    :param timeout: A floating point number specifying the socket timeout in
                    seconds. None means to use the default which is 30 seconds.
    :param retry_wait: A floating point number specifying how many seconds to
                       wait between each retry. None means to use the default
                       which is 5 seconds.
    """

  def __init__(self, host, port=8009, device=None, *args, **kwargs):
    self._metadata = DeviceMetadata.create_from_host(host)
    if not self._metadata:
      raise error.ChromecastConnectionError(
          'Could not connect to {0}'.format(host))

    self.status = None
    self.status_event = threading.Event()

    self._socket_client = socket_client.SocketClient(
        host=host,
        port=port,
        cast_type=self._metadata.cast_type,
        tries=None,
        timeout=None,
        retry_wait=None,
        blocking=True)

    receiver_controller = self._socket_client.receiver_controller
    receiver_controller.register_status_listener(self)

    # Forward these methods
    self.set_volume = receiver_controller.set_volume
    self.set_volume_muted = receiver_controller.set_volume_muted
    self.play_media = self._socket_client.media_controller.play_media
    self.register_handler = self._socket_client.register_handler
    self.register_status_listener = \
        receiver_controller.register_status_listener
    self.register_launch_error_listener = \
        receiver_controller.register_launch_error_listener
    self.register_connection_listener = \
        self._socket_client.register_connection_listener

    self._socket_client.start()

  @property
  def ignore_cec(self):
    """ Returns whether the CEC data should be ignored. """
    return self._metadata is not None and \
        any([fnmatch.fnmatchcase(self._metadata.friendly_name, pattern)
             for pattern in IGNORE_CEC])

  @property
  def is_idle(self):
    """ Returns if there is currently an app running. """
    return (self.status is None or self.app_id in (None, IDLE_APP_ID) or
            (not self.status.is_active_input and not self.ignore_cec))

  @property
  def metadata(self):
    return self._metadata

  @property
  def uri(self):
    """ Returns the device URI (ip:port) """
    return "{}:{}".format(self.host, self.port)

  @property
  def app_id(self):
    """ Returns the current app_id. """
    return self.status.app_id if self.status else None

  @property
  def app_display_name(self):
    """ Returns the name of the current running app. """
    return self.status.display_name if self.status else None

  @property
  def media_controller(self):
    return self._socket_client.media_controller

  def new_cast_status(self, status):
    """ Called when a new status received from the Chromecast. """
    self.status = status
    if status:
      self.status_event.set()

  def start_app(self, app_id, force_launch=False):
    """ Start an app on the Chromecast. """
    self.logger.info("Starting app %s", app_id)

    self._socket_client.receiver_controller.launch_app(app_id, force_launch)

  def quit_app(self):
    """ Tells the Chromecast to quit current app_id. """
    self.logger.info("Quiting current app")

    self._socket_client.receiver_controller.stop_app()

  def reboot(self):
    """ Reboots the Chromecast. """
    reboot(self.host)

  def volume_up(self, delta=0.1):
    """ Increment volume by 0.1 (or delta) unless it is already maxed.
        Returns the new volume.

        """
    if delta <= 0:
      raise ValueError(
          "volume delta must be greater than zero, not {}".format(delta))
    return self.set_volume(self.status.volume_level + delta)

  def volume_down(self, delta=0.1):
    """ Decrement the volume by 0.1 (or delta) unless it is already 0.
        Returns the new volume.
        """
    if delta <= 0:
      raise ValueError(
          "volume delta must be greater than zero, not {}".format(delta))
    return self.set_volume(self.status.volume_level - delta)

  def wait(self, timeout=None):
    """
        Waits until the cast device is ready for communication. The device
        is ready as soon a status message has been received.

        If the status has already been received then the method returns
        immediately.

        :param timeout: a floating point number specifying a timeout for the
                        operation in seconds (or fractions thereof). Or None
                        to block forever.
        """
    self.status_event.wait(timeout=timeout)

  def disconnect(self, timeout=None, blocking=True):
    """
        Disconnects the chromecast and waits for it to terminate.

        :param timeout: a floating point number specifying a timeout for the
                        operation in seconds (or fractions thereof). Or None
                        to block forever.
        :param blocking: If True it will block until the disconnection is
                         complete, otherwise it will return immediately.
        """
    self._socket_client.disconnect()
    if blocking:
      self.join(timeout=timeout)

  def join(self, timeout=None):
    """
        Blocks the thread of the caller until the chromecast connection is
        stopped.

        :param timeout: a floating point number specifying a timeout for the
                        operation in seconds (or fractions thereof). Or None
                        to block forever.
        """
    self._socket_client.join(timeout=timeout)

  def __del__(self):
    try:
      self._socket_client.stop.set()
    except AttributeError:
      pass

  def __repr__(self):
    txt = "Chromecast({!r}, port={!r}, device={!r})".format(
        self.host, self.port, self._metadata)
    return txt

  def __unicode__(self):
    return "Chromecast({}, {}, {}, {}, {})".format(
        self.host, self.port, self._metadata.friendly_name,
        self._metadata.model_name, self._metadata.manufacturer)