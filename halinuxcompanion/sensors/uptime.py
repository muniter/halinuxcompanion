from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil
from datetime import datetime

Uptime = Sensor()
Uptime.device_class = "timestamp"
Uptime.icon = "mdi:clock"
Uptime.name = "Uptime"
Uptime.state = 0
Uptime.type = "sensor"
Uptime.unique_id = "uptime"
Uptime.unit_of_measurement = ""

def updater(self):
    self.state = datetime.fromtimestamp(psutil.boot_time()).isoformat()

Uptime.updater = MethodType(updater, Uptime)


