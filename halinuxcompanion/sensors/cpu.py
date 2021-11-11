from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil
import os

load_average: bool = False

Cpu = Sensor()
Cpu.attributes = {
    "cpu_count": psutil.cpu_count(logical=False),
    "cpu_logical_count": psutil.cpu_count(),
}

if os.name == "posix":
    load_average = True

Cpu.device_class = "power_factor"
Cpu.icon = "mdi:cpu-64-bit"
Cpu.name = "CPU Load"
Cpu.state = 0
Cpu.type = "sensor"
Cpu.unique_id = "cpu_load"
Cpu.unit_of_measurement = "%"

def updater(self):
    self.state = psutil.cpu_percent()
    if load_average:
        data = psutil.getloadavg()
        self.attributes["load_1"] = data[0]
        self.attributes["load_5"] = data[1]
        self.attributes["load_15"] = data[2]

Cpu.updater = MethodType(updater, Cpu)
