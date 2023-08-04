from types import MethodType
from halinuxcompanion.sensor import Sensor
from glob import glob
from subprocess import run
from logging import getLogger

CameraState = Sensor()
CameraState.config_name = "camera_state"
CameraState.attributes = {}

CameraState.icon = "mdi:video-off"
CameraState.name = "Camera State"
CameraState.state = "unavailable"
CameraState.type = "sensor"
CameraState.unique_id = "camera_state"

def updater(self):
    logger = getLogger(__name__)

    ''' Get list of /dev/video* devices '''
    devices = glob("/dev/video*")

    ''' Call fuser to check if any camera is being used '''
    output = run(["fuser"] + devices, capture_output=True, check=False).stdout
    output = output.decode("utf-8")
    logger.debug(f"CameraState: {output}")
    if output == "":
        self.state = "idle"
        self.icon = "mdi:video-off"
    else:
        self.state = "active"
        self.icon = "mdi:video"

CameraState.updater = MethodType(updater, CameraState)
