from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil
import os

load_average: bool = False
allow_update: bool = True

Cpu = Sensor()
Cpu.config_name = "cpu"
Cpu.attributes = {
    "cpu_count": psutil.cpu_count(logical=False),
    "cpu_logical_count": psutil.cpu_count(),
}

if os.name == "posix":
    load_average = True

Cpu.device_class = "power_factor"
Cpu.state_class = "measurement"
Cpu.icon = "mdi:cpu-64-bit"
Cpu.name = "CPU Load"
Cpu.state = 0
Cpu.type = "sensor"
Cpu.unique_id = "cpu_load"
Cpu.unit_of_measurement = "%"


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

    self.state = psutil.cpu_percent()
    if load_average:
        data = psutil.getloadavg()
        self.attributes["load_1"] = data[0]
        self.attributes["load_5"] = data[1]
        self.attributes["load_15"] = data[2]


Cpu.updater = MethodType(updater, Cpu)
Cpu.signals = {
    "system.login_on_prepare_for_sleep": on_prepare_for_sleep,
    "system.login_on_prepare_for_shutdown": on_prepare_for_shutdown,
}
