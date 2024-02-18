from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil

allow_update: bool = True

Memory = Sensor()
Memory.config_name = "memory"
Memory.attributes = {
    "total": 0,
    "available": 0,
    "used": 0,
    "free": 0,
}

Memory.device_class = "power_factor"
Memory.state_class = "measurement"
Memory.icon = "mdi:memory"
Memory.name = "Memory Load"
Memory.state = 0
Memory.type = "sensor"
Memory.unique_id = "memory_usage"
Memory.unit_of_measurement = "%"


async def on_prepare_for_sleep(self, v):
    """Handler for system sleep and wake up from sleep events.
    https://www.freedesktop.org/software/systemd/man/org.freedesktop.login1.html

    :param v: True if going to sleep, False if waking up from it
    """
    global allow_update
    if v:
        allow_update = False
        self.state = "unavailable"
    else:
        allow_update = True


async def on_prepare_for_shutdown(self, v):
    """Handler for system shutdown/reboot.
    https://www.freedesktop.org/software/systemd/man/org.freedesktop.login1.html

    :param v: True if shutting down, False if powering on.
    """
    global allow_update
    if v:
        allow_update = False
        self.state = "unavailable"
    else:
        allow_update = True


def updater(self):
    if not allow_update:
        return

    data = psutil.virtual_memory()
    self.state = round((data.total - data.available) / data.total * 100, 1)
    self.attributes["total"] = data.total / 1024
    self.attributes["available"] = data.available / 1024
    self.attributes["used"] = data.used / 1024
    self.attributes["free"] = data.free / 1024


Memory.updater = MethodType(updater, Memory)
Memory.signals = {
    "system.login_on_prepare_for_sleep": on_prepare_for_sleep,
    "system.login_on_prepare_for_shutdown": on_prepare_for_shutdown,
}
