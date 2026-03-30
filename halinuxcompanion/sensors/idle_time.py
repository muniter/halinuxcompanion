from halinuxcompanion.sensor import Sensor
from subprocess import run
from types import MethodType

IdleTime = Sensor()
IdleTime.type = "sensor"
IdleTime.config_name = "idle_time"
IdleTime.unique_id = "idle_time"
IdleTime.name = "Idle time"
IdleTime.icon = "mdi:progress-clock"

IdleTime.device_class = "duration"
IdleTime.state_class = "total_increasing"
IdleTime.unit_of_measurement = "min"
IdleTime.state = 0  # initial state only

def updater(self):
    self.state = float(run(["xprintidle"], capture_output=True, text=True).stdout) / 1000 / 60

IdleTime.updater = MethodType(updater, IdleTime)
