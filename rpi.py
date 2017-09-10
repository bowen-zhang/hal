import subprocess


class RaspberryPi(object):

  @staticmethod
  def get_cpu_temperature():
    process = subprocess.Popen(
        ['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE)
    output, _error = process.communicate()
    return float(output.replace("temp=", "").replace("'C\n", ""))
