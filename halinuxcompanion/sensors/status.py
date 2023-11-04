from types import MethodType
from halinuxcompanion.sensor import Sensor
import psutil
import os

import logging

logger = logging.getLogger(__name__)

Status = Sensor()
Status.config_name = "status"
Status.type = "binary_sensor"
Status.device_class = "power"
Status.name = "Status"
Status.unique_id = "status"
Status.icon = "mdi:cpu-64-bit"

Status.state = True
Status.attributes = {"reason": "power_on", "idle": "unknown"}

IDLE = {True: {"idle": "true"}, False: {"idle": "false"}}
SLEEP = {True: {"reason": "sleep"}, False: {"reason": "wake"}}
SHUTDOWN = {True: {"reason": "power_off"}, False: {"reason": "power_on"}}


async def on_prepare_for_sleep(self, v):
    """Handler for system sleep and wake up from sleep events.
    https://www.freedesktop.org/software/systemd/man/org.freedesktop.login1.html

    :param v: True if going to sleep, False if waking up from it
    """
    self.state = not v
    self.attributes = SLEEP[v]


async def on_prepare_for_shutdown(self, v):
    """Handler for system shutdown/reboot.
    https://www.freedesktop.org/software/systemd/man/org.freedesktop.login1.html

    :param v: True if shutting down, False if powering on.
    """
    self.state = not v
    self.attributes = SHUTDOWN[v]


async def screensaver_on_active_changed(self, v):
    """Handler for session screensaver status changes."""
    self.attributes.update(IDLE[v])


def updater(self):
    pass


Status.updater = MethodType(updater, Status)
Status.signals = {
    "system.login_on_prepare_for_sleep": on_prepare_for_sleep,
    "system.login_on_prepare_for_shutdown": on_prepare_for_shutdown,
    "session.screensaver_on_active_changed": screensaver_on_active_changed,
    "session.gnome_screensaver_on_active_changed": screensaver_on_active_changed,
}
