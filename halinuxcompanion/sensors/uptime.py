from halinuxcompanion.sensor import Sensor
import psutil
import pytz
from datetime import datetime

Uptime = Sensor()
Uptime.device_class = "timestamp"
Uptime.state_class = "measurement"
Uptime.icon = "mdi:clock"
Uptime.name = "Uptime"
Uptime.state = 0
Uptime.type = "sensor"
Uptime.unique_id = "uptime"
Uptime.unit_of_measurement = ""
Uptime.state = datetime.fromtimestamp(psutil.boot_time(), pytz.UTC).isoformat()
