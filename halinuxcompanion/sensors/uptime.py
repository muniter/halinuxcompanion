from halinuxcompanion.sensor import Sensor
import psutil
from datetime import datetime, timezone

Uptime = Sensor()
Uptime.config_name = "uptime"
Uptime.device_class = "timestamp"
Uptime.state_class = ""
Uptime.icon = "mdi:clock"
Uptime.name = "Uptime"
Uptime.state = 0
Uptime.type = "sensor"
Uptime.unique_id = "uptime"
Uptime.unit_of_measurement = ""
Uptime.state = datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat()
