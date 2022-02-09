from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil

BatteryState = Sensor()
BatteryState.attributes = {}

BatteryState.icon = "mdi:battery"
BatteryState.name = "Battery State"
BatteryState.state = ""
BatteryState.type = "sensor"
BatteryState.unique_id = "battery_state"


def updater(self):
    data = psutil.sensors_battery()

    if data.power_plugged:
        self.state = "charging"
        self.icon = "mdi:battery-plus"
    else:
        self.state = "discharging"
        self.icon = "mdi:battery-minus"


BatteryState.updater = MethodType(updater, BatteryState)
