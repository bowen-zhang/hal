import sense_hat

from common import pattern
from common import unit


class SenseHat(pattern.Singleton, pattern.EventEmitter):

    def __init__(selfm *args, **kwargs):
        super(SenseHat, self).__init__(*args, **kwargs)
        self._sense = sense_hat.SenseHat()

        self._sense.set_imu_config(
            compass_enabled=True, gyro_enabled=True, accel_enabled=True)
        self._sense.stick.direction_middle = self._on_joystick_pushed

    @property
    def pitch(self):
        orientation = self._sense.get_orientation_degrees()
        return unit.Angle(orientation['pitch'], unit.Angle.DEGREE, unit.Angle.RELATIVE_RANGE)

    @property
    def roll(self):
        orientation = self._sense.get_orientation_degrees()
        return unit.Angle(orientation['roll'], unit.Angle.DEGREE, unit.Angle.RELATIVE_RANGE)

    @property
    def heading(self):
        return unit.Angle(self._sense.get_compass(), unit.Angle.DEGREE, unit.Angle.HEADING_RANGE)

    @property
    def temperature(self):
        return unit.Temperature(self._sense.get_temperature(), unit.Temperature.CELSIUS)

    @property
    def pressure(self):
        return unit.Pressure(self._sense.get_pressure(), unit.Pressure.MILLIBAR)

    @property
    def humidity(self):
        return self._sense.get_humidity()

    def _on_joystick_pushed(self):
        self.emit('joystick_pushed', self)
'''
