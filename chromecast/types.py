import enum


class CastType(enum.Enum):
  CHROMECAST = 'cast'  # video & audio
  AUDIO = 'audio'  # audio only
  GROUP = 'group'  # audio only


CAST_TYPE_MAPPING = {
    'chromecast': CastType.CHROMECAST,
    'eureka dongle': CastType.CHROMECAST,
    'chromecast audio': CastType.AUDIO,
    'google home': CastType.AUDIO,
    'google cast group': CastType.GROUP,
}
