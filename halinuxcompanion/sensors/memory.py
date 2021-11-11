from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil

Memory = Sensor()
Memory.attributes = {
    "total": 0,
    "available": 0,
    "used": 0,
    "free": 0,
}

Memory.device_class = "power_factor"
Memory.icon = "mdi:memory"
Memory.name = "Memory Load"
Memory.state = 0
Memory.type = "sensor"
Memory.unique_id = "memory_usage"
Memory.unit_of_measurement = "%"


def updater(self):
    data = psutil.virtual_memory()
    self.state = round((data.total - data.available) / data.total * 100, 1)
    self.attributes["total"] = data.total / 1024
    self.attributes["available"] = data.available / 1024
    self.attributes["used"] = data.used / 1024
    self.attributes["free"] = data.free / 1024


Memory.updater = MethodType(updater, Memory)
