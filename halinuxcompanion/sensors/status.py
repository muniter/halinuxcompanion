from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil
import os

import logging

logger = logging.getLogger(__name__)

load_average: bool = False

Status = Sensor()
Status.attributes = {
    "cpu_count": psutil.cpu_count(logical=False),
    "cpu_logical_count": psutil.cpu_count(),
}

if os.name == "posix":
    load_average = True

Status.type = "binary_sensor"
Status.device_class = "power"
Status.name = "Computer status"
Status.unique_id = "status"
Status.icon = "mdi:cpu-64-bit"

Status.state = "on"
Status.attributes = {"reason": "power_on"}


async def on_prepare_for_sleep(self, v):
    if v:
        self.status = "off"
        self.attributes = {"reason": "sleep"}
    else:
        self.status = "on"
        self.attributes = {"reason": "wake"}


async def on_prepare_for_shutdown(self, v):
    if v:
        self.status = "off"
        self.attributes = {"reason": "shutdown"}
    else:
        self.status = "on"
        self.attributes = {"reason": "power_on"}


def updater(self):
    # TODO: If computer is still on after "sleep", it should set to on
    self
    pass


Status.updater = MethodType(updater, Status)
Status.signals = {
    "system.login_on_prepare_for_sleep": on_prepare_for_sleep,
    "system.login_on_prepare_for_shutdown": on_prepare_for_shutdown,
}
