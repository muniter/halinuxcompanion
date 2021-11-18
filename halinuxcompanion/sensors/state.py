from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil
import os

import logging

logger = logging.getLogger(__name__)

load_average: bool = False

State = Sensor()
State.attributes = {
    "cpu_count": psutil.cpu_count(logical=False),
    "cpu_logical_count": psutil.cpu_count(),
}

if os.name == "posix":
    load_average = True

State.type = "binary_sensor"
State.device_class = "power"
State.name = "Computer state"
State.unique_id = "state"
State.icon = "mdi:cpu-64-bit"

State.state = "on"
State.attributes = {"reason": "power_on"}


async def on_prepare_for_sleep(self, v):
    if v:
        self.state = "off"
        self.attributes = {"reason": "sleep"}
    else:
        self.state = "on"
        self.attributes = {"reason": "wake"}


async def on_prepare_for_shutdown(self, v):
    if v:
        self.state = "off"
        self.attributes = {"reason": "shutdown"}
    else:
        self.state = "on"
        self.attributes = {"reason": "power_on"}


def updater(self):
    # TODO: If computer is still on after "sleep", it should set to on
    self
    pass


State.updater = MethodType(updater, State)
State.signals = {
    "system.login_on_prepare_for_sleep": on_prepare_for_sleep,
    "system.login_on_prepare_for_shutdown": on_prepare_for_shutdown,
}
