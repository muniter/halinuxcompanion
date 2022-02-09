from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil

BatteryLevel = Sensor()
BatteryLevel.config_name = "battery_level"
BatteryLevel.attributes = {
        "time_left": "",
}

BatteryLevel.device_class = "battery"
BatteryLevel.state_class = "measurement"
BatteryLevel.icon = "mdi:battery"
BatteryLevel.name = "Battery Level"
BatteryLevel.state = "unavailable"
BatteryLevel.type = "sensor"
BatteryLevel.unique_id = "battery_level"
BatteryLevel.unit_of_measurement = "%"


def updater(self):
    data = psutil.sensors_battery()
    if data is not None:
        minutes, seconds = divmod(data.secsleft, 60)
        hours, minutes = divmod(minutes, 60)

        self.state = round(data.percent)
        self.icon = "mdi:battery-%d0" % round(data.percent / 10)
        self.attributes["time_left"] = "%d:%02d:%02d" % (hours, minutes, seconds)


BatteryLevel.updater = MethodType(updater, BatteryLevel)
