from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil
import os

import logging

logger = logging.getLogger(__name__)

load_average: bool = False

Status = Sensor()
Status.config_name = "status"
Status.attributes = {
    "cpu_count": psutil.cpu_count(logical=False),
    "cpu_logical_count": psutil.cpu_count(),
}

if os.name == "posix":
    load_average = True

Status.type = "binary_sensor"
Status.device_class = "power"
Status.name = "Status"
Status.unique_id = "status"
Status.icon = "mdi:cpu-64-bit"

Status.state = True
Status.attributes = {"reason": "power_on"}

sleep = {True: {"reason": "sleep"}, False: {"reason": "wake"}}
shutdown = {True: {"reason": "power_off"}, False: {"reason": "power_on"}}


async def on_prepare_for_sleep(self, v):
    """Handler for system sleep and wake up from sleep events.
    https://www.freedesktop.org/software/systemd/man/org.freedesktop.login1.html

    :param v: True if going to sleep, False if waking up from it
    """
    self.state = not v
    self.attributes = sleep[v]


async def on_prepare_for_shutdown(self, v):
    """Handler for system shutdown/reboot.
    https://www.freedesktop.org/software/systemd/man/org.freedesktop.login1.html

    :param v: True if shuting down, False if powering on.
    """
    self.state = not v
    self.attributes = shutdown[v]


def updater(self):
    # TODO: If computer is still on after "sleep", it should set to on
    self
    pass


Status.updater = MethodType(updater, Status)
Status.signals = {
    "system.login_on_prepare_for_sleep": on_prepare_for_sleep,
    "system.login_on_prepare_for_shutdown": on_prepare_for_shutdown,
}
