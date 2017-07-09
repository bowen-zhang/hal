import ctypes
import datetime
import enum
import math
import smbus
import time

from hal.LSM9DS0 import *
from common import pattern
from common import unit


# return two bytes from data as a signed 16-bit value
def _get_short(data, index):
  return ctypes.c_short((data[index] << 8) + data[index + 1]).value


# return two bytes from data as an unsigned 16-bit value
def _get_ushort(data, index):
  return (data[index] << 8) + data[index + 1]


class _Axis(enum.Enum):
  X = 0
  Y = 1
  Z = 2


class IMUBus(pattern.Singleton):
  ACC_REG_LOW = [OUT_X_L_A, OUT_Y_L_A, OUT_Z_L_A]
  ACC_REG_HIGH = [OUT_X_H_A, OUT_Y_H_A, OUT_Z_H_A]
  MAG_REG_LOW = [OUT_X_L_M, OUT_Y_L_M, OUT_Z_L_M]
  MAG_REG_HIGH = [OUT_X_H_M, OUT_Y_H_M, OUT_Z_H_M]
  GYRO_REG_LOW = [OUT_X_L_G, OUT_Y_L_G, OUT_Z_L_G]
  GYRO_REG_HIGH = [OUT_X_H_G, OUT_Y_H_G, OUT_Z_H_G]

  def __init__(self, *args, **kwargs):
    super(IMUBus, self).__init__(*args, **kwargs)
    self._bus = smbus.SMBus(1)
    self.write_acc(
        CTRL_REG1_XM,
        0b01100111)  #z,y,x axis enabled, continuos update,  100Hz data rate
    self.write_acc(CTRL_REG2_XM, 0b00100000)  #+/- 16G full scale

    #initialise the magnetometer
    self.write_mag(CTRL_REG5_XM, 0b11110000)  #Temp enable, M data rate = 50Hz
    self.write_mag(CTRL_REG6_XM, 0b01100000)  #+/-12gauss
    self.write_mag(CTRL_REG7_XM, 0b00000000)  #Continuous-conversion mode

    #initialise the gyroscope
    self.write_gyro(CTRL_REG1_G,
                    0b00001111)  #Normal power mode, all axes enabled
    self.write_gyro(CTRL_REG4_G,
                    0b00110000)  #Continuos update, 2000 dps full scale

  def write_env(self, register, value):
    self._bus.write_byte_data(ENV_ADDRESS, register, value)

  def read_env(self, register, value):
    return self._bus.read_i2c_block_data(ENV_ADDRESS, register, value)

  def write_acc(self, register, value):
    self._bus.write_byte_data(ACC_ADDRESS, register, value)

  def read_acc(self, axis):
    return self._read(IMUBus.ACC_REG_LOW[axis.value],
                      IMUBus.ACC_REG_HIGH[axis.value])

  def write_mag(self, register, value):
    self._bus.write_byte_data(MAG_ADDRESS, register, value)

  def read_mag(self, axis):
    return self._read(IMUBus.MAG_REG_LOW[axis.value],
                      IMUBus.MAG_REG_HIGH[axis.value])

  def write_gyro(self, register, value):
    self._bus.write_byte_data(GYR_ADDRESS, register, value)

  def read_gyro(self, axis):
    return self._read(IMUBus.GYRO_REG_LOW[axis.value],
                      IMUBus.GYRO_REG_HIGH[axis.value])

  def _read(self, low, high):
    acc_l = self._bus.read_byte_data(ACC_ADDRESS, low)
    acc_h = self._bus.read_byte_data(ACC_ADDRESS, high)
    acc_combined = (acc_l | acc_h << 8)
    return acc_combined if acc_combined < 32768 else acc_combined - 65536


class Load(object):

  def __init__(self):
    self._bus = IMUBus.get_instance()

  @property
  def x(self):
    value = self._bus.read_acc(_Axis.X)
    return value * 0.732 / 1000

  @property
  def y(self):
    value = self._bus.read_acc(_Axis.Y)
    return value * 0.732 / 1000

  @property
  def z(self):
    value = self._bus.read_acc(_Axis.Z)
    return value * 0.732 / 1000


class Environment(object):

  _OVERSAMPLING = 3

  def __init__(self):
    self._bus = IMUBus.get_instance()

    # Read whole calibration EEPROM data
    cal = self._bus.read_env(0xAA, 22)
    # Convert byte data to word values
    self._ac1 = _get_short(cal, 0)
    self._ac2 = _get_short(cal, 2)
    self._ac3 = _get_short(cal, 4)
    self._ac4 = _get_ushort(cal, 6)
    self._ac5 = _get_ushort(cal, 8)
    self._ac6 = _get_ushort(cal, 10)
    self._b1 = _get_short(cal, 12)
    self._b2 = _get_short(cal, 14)
    self._mb = _get_short(cal, 16)
    self._mc = _get_short(cal, 18)
    self._md = _get_short(cal, 20)

  @property
  def temperature(self):
    self._update()
    return self._temperature

  @property
  def pressure(self):
    self._update()
    return self._pressure

  @property
  def humidity(self):
    return None

  @property
  def temperature_pressure(self):
    self._update()
    return (self._temperature, self._pressure)

  def _update(self):
    # Get raw temperature
    self._bus.write_env(0xF4, 0x2E)
    time.sleep(0.005)
    (msb, lsb) = self._bus.read_env(0xF6, 2)
    ut = (msb << 8) + lsb

    # Calculating temperature
    x1 = ((ut - self._ac6) * self._ac5) >> 15
    x2 = (self._mc << 11) / (x1 + self._md)
    b5 = x1 + x2
    t = (b5 + 8) >> 4

    # Get raw pressure
    self._bus.write_env(0xF4, 0x34 + (Environment._OVERSAMPLING << 6))
    time.sleep(0.04)
    (msb, lsb, xsb) = self._bus.read_env(0xF6, 3)
    up = ((msb << 16) + (lsb << 8) + xsb) >> (8 - Environment._OVERSAMPLING)

    # Calculating pressure
    b6 = b5 - 4000
    b62 = b6 * b6 >> 12
    x1 = (self._b2 * b62) >> 11
    x2 = self._ac2 * b6 >> 11
    x3 = x1 + x2
    b3 = (((self._ac1 * 4 + x3) << Environment._OVERSAMPLING) + 2) >> 2

    x1 = self._ac3 * b6 >> 13
    x2 = (self._b1 * b62) >> 16
    x3 = ((x1 + x2) + 2) >> 2
    b4 = (self._ac4 * (x3 + 32768)) >> 15
    b7 = (up - b3) * (50000 >> Environment._OVERSAMPLING)

    p = (b7 * 2) / b4
    #p = (b7 / b4) * 2

    x1 = (p >> 8) * (p >> 8)
    x1 = (x1 * 3038) >> 16
    x2 = (-7357 * p) >> 16
    p = p + ((x1 + x2 + 3791) >> 4)

    self._temperature = unit.Temperature(t / 10.0, unit.Temperature.CELSIUS)
    self._pressure = unit.Pressure(p, unit.Pressure.PA)


class Attitude(object):

  def __init__(self):
    self._bus = IMUBus.get_instance()

    self._gyroXangle = 0.0
    self._gyroYangle = 0.0
    self._gyroZangle = 0.0
    self._CFangleX = 0.0
    self._CFangleY = 0.0

  @property
  def pitch(self):
    #Read the accelerometer,gyroscope and magnetometer values
    ACCx = self._bus.read_acc(_Axis.X)
    ACCy = self._bus.read_acc(_Axis.Y)
    ACCz = self._bus.read_acc(_Axis.Z)

    #Normalize accelerometer raw values.
    accXnorm = ACCx / math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)

    ####################################################################
    ###################Calculate pitch and roll#########################
    ####################################################################
    #Use these two lines when the IMU is up the right way. Skull logo is facing down
    pitch = math.asin(accXnorm)
    #
    #Us these four lines when the IMU is upside down. Skull logo is facing up
    #accXnorm = -accXnorm               #flip Xnorm as the IMU is upside down
    #pitch = math.asin(accXnorm)
    #
    ############################ END ##################################
    return unit.Angle(pitch, unit.Angle.RADIAN, unit.Angle.RELATIVE_RANGE)

  @property
  def roll(self):
    #Read the accelerometer,gyroscope and magnetometer values
    ACCx = self._bus.read_acc(_Axis.X)
    ACCy = self._bus.read_acc(_Axis.Y)
    ACCz = self._bus.read_acc(_Axis.Z)

    #Normalize accelerometer raw values.
    accXnorm = ACCx / math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)
    accYnorm = ACCy / math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)

    ####################################################################
    ###################Calculate pitch and roll#########################
    ####################################################################
    #Use these two lines when the IMU is up the right way. Skull logo is facing down
    pitch = math.asin(accXnorm)
    roll = -math.asin(accYnorm / math.cos(pitch))
    #
    #Us these four lines when the IMU is upside down. Skull logo is facing up
    #accXnorm = -accXnorm               #flip Xnorm as the IMU is upside down
    #accYnorm = -accYnorm               #flip Ynorm as the IMU is upside down
    #pitch = math.asin(accXnorm)
    #roll = math.asin(accYnorm/math.cos(pitch))
    #
    ############################ END ##################################
    return unit.Angle(roll, unit.Angle.RADIAN, unit.Angle.RELATIVE_RANGE)

  @property
  def heading(self):
    MAGx = self._bus.read_mag(_Axis.X)
    MAGy = self._bus.read_mag(_Axis.Y)
    ####################################################################
    ############################MAG direction ##########################
    ####################################################################
    #If IMU is upside down, then use this line.  It isnt needed if the
    # IMU is the correct way up
    #MAGy = -MAGy
    #
    ############################ END ##################################

    #Calculate heading
    heading = math.atan2(MAGy, MAGx)
    return unit.Angle(heading, unit.Angle.RADIAN, unit.Angle.HEADING_RANGE)

  '''
RAD_TO_DEG = 57.29578
M_PI = 3.14159265358979323846
G_GAIN = 0.070  # [deg/s/LSB]  If you change the dps for gyro, you need to update this value accordingly
AA =  0.40      # Complementary filter constant

#Kalman filter variables
Q_angle = 0.02
Q_gyro = 0.0015
R_angle = 0.005
y_bias = 0.0
x_bias = 0.0
XP_00 = 0.0
XP_01 = 0.0
XP_10 = 0.0
XP_11 = 0.0
YP_00 = 0.0
YP_01 = 0.0
YP_10 = 0.0
YP_11 = 0.0
KFangleX = 0.0
KFangleY = 0.0


def _kalmanFilterY(accAngle, gyroRate, DT):
    y=0.0
    S=0.0

    global KFangleY
    global Q_angle
    global Q_gyro
    global y_bias
    global YP_00
    global YP_01
    global YP_10
    global YP_11

    KFangleY = KFangleY + DT * (gyroRate - y_bias)

    YP_00 = YP_00 + ( - DT * (YP_10 + YP_01) + Q_angle * DT )
    YP_01 = YP_01 + ( - DT * YP_11 )
    YP_10 = YP_10 + ( - DT * YP_11 )
    YP_11 = YP_11 + ( + Q_gyro * DT )

    y = accAngle - KFangleY
    S = YP_00 + R_angle
    K_0 = YP_00 / S
    K_1 = YP_10 / S

    KFangleY = KFangleY + ( K_0 * y )
    y_bias = y_bias + ( K_1 * y )

    YP_00 = YP_00 - ( K_0 * YP_00 )
    YP_01 = YP_01 - ( K_0 * YP_01 )
    YP_10 = YP_10 - ( K_1 * YP_00 )
    YP_11 = YP_11 - ( K_1 * YP_01 )

    return KFangleY

def _kalmanFilterX(accAngle, gyroRate, DT):
    x=0.0
    S=0.0

    global KFangleX
    global Q_angle
    global Q_gyro
    global x_bias
    global XP_00
    global XP_01
    global XP_10
    global XP_11


    KFangleX = KFangleX + DT * (gyroRate - x_bias)

    XP_00 = XP_00 + ( - DT * (XP_10 + XP_01) + Q_angle * DT )
    XP_01 = XP_01 + ( - DT * XP_11 )
    XP_10 = XP_10 + ( - DT * XP_11 )
    XP_11 = XP_11 + ( + Q_gyro * DT )

    x = accAngle - KFangleX
    S = XP_00 + R_angle
    K_0 = XP_00 / S
    K_1 = XP_10 / S

    KFangleX = KFangleX + ( K_0 * x )
    x_bias = x_bias + ( K_1 * x )

    XP_00 = XP_00 - ( K_0 * XP_00 )
    XP_01 = XP_01 - ( K_0 * XP_01 )
    XP_10 = XP_10 - ( K_1 * XP_00 )
    XP_11 = XP_11 - ( K_1 * XP_01 )

    return KFangleX

    def _on_start(self):
        self._a = time.time()

    def _on_run(self):
        #Read the accelerometer,gyroscope and magnetometer values
        ACCx = readACCx()
        ACCy = readACCy()
        ACCz = readACCz()
        GYRx = readGYRx()
        GYRy = readGYRy()
        GYRz = readGYRz()
        MAGx = readMAGx()
        MAGy = readMAGy()
        MAGz = readMAGz()

        ####################################################################
        ############################MAG direction ##########################
        ####################################################################
        #If IMU is upside down, then use this line.  It isnt needed if the
        # IMU is the correct way up
        #MAGy = -MAGy
        #
        ############################ END ##################################

        #Normalize accelerometer raw values.
        accXnorm = ACCx/math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)
        accYnorm = ACCy/math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)

        ####################################################################
        ###################Calculate pitch and roll#########################
        ####################################################################
        #Use these two lines when the IMU is up the right way. Skull logo is facing down
        pitch = math.asin(accXnorm)
        roll = -math.asin(accYnorm/math.cos(pitch))
        #
        #Us these four lines when the IMU is upside down. Skull logo is facing up
        #accXnorm = -accXnorm               #flip Xnorm as the IMU is upside down
        #accYnorm = -accYnorm               #flip Ynorm as the IMU is upside down
        #pitch = math.asin(accXnorm)
        #roll = math.asin(accYnorm/math.cos(pitch))
        #
        ############################ END ##################################

        #Calculate heading
        heading = 180 * math.atan2(MAGy,MAGx)/M_PI
        #Only have our heading between 0 and 360
        if heading < 0:
            heading += 360

        #Calculate the new tilt compensated values
        magXcomp = MAGx*math.cos(pitch)+MAGz*math.sin(pitch)
        magYcomp = MAGx*math.sin(roll)*math.sin(pitch)+MAGy*math.cos(roll)-MAGz*math.sin(roll)*math.cos(pitch)

        #Calculate tilt compensated heading
        tiltCompensatedHeading = 180 * math.atan2(magYcomp,magXcomp)/M_PI
        if tiltCompensatedHeading < 0:
                tiltCompensatedHeading += 360

        #Convert Gyro raw to degrees per second
        rate_gyr_x =  GYRx * G_GAIN
        rate_gyr_y =  GYRy * G_GAIN
        rate_gyr_z =  GYRz * G_GAIN

        ##Calculate loop Period(LP). How long between Gyro Reads
        now = time.time()
        LP = (now - self._a) * 1000.0
        self._a = now

        #Calculate the angles from the gyro.
        self._gyroXangle += rate_gyr_x*LP
        self._gyroYangle += rate_gyr_y*LP
        self._gyroZangle += rate_gyr_z*LP

        ##Convert Accelerometer values to degrees
        AccXangle =  (math.atan2(ACCy,ACCz)+M_PI)*RAD_TO_DEG
        AccYangle =  (math.atan2(ACCz,ACCx)+M_PI)*RAD_TO_DEG

        ####################################################################
        ######################Correct rotation value########################
        ####################################################################
        #Change the rotation value of the accelerometer to -/+ 180 and
            #move the Y axis '0' point to up.
            #
            #Two different pieces of code are used depending on how your IMU is mounted.
        #If IMU is up the correct way, Skull logo is facing down, Use these lines
        AccXangle -= 180.0
        if AccYangle > 90:
            AccYangle -= 270.0
        else:
            AccYangle += 90.0
        #
        #
        #If IMU is upside down E.g Skull logo is facing up;
        #if AccXangle >180:
            #        AccXangle -= 360.0
        #AccYangle-=90
        #if (AccYangle >180):
            #        AccYangle -= 360.0
        ############################ END ##################################

        #Complementary filter used to combine the accelerometer and gyro values.
        self._CFangleX=AA*(self._CFangleX+rate_gyr_x*LP) +(1 - AA) * AccXangle
        self._CFangleY=AA*(self._CFangleY+rate_gyr_y*LP) +(1 - AA) * AccYangle

        #Kalman filter used to combine the accelerometer and gyro values.
        kalmanY = kalmanFilterY(AccYangle, rate_gyr_y,LP)
        kalmanX = kalmanFilterX(AccXangle, rate_gyr_x,LP)

        self._pitch = pitch
        self._roll = roll
        self._heading = heading

        time.sleep(0.03)
    '''
