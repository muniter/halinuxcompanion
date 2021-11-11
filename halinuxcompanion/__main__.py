from halinuxcompanion.api import API
from halinuxcompanion.companion import Companion
from halinuxcompanion.sensors.cpu import Cpu
from halinuxcompanion.sensors.memory import Memory
from halinuxcompanion.sensors.uptime import Uptime

from time import sleep
import json
import logging
# set logging level using and environment variable
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
config = "config.json"


def load_config() -> dict:
    with open(config, "r") as f:
        return json.load(f)


def main():
    # TOOD: implement config file
    logger.info("Reading configuration file")
    config = load_config()
    companion = Companion(config)
    api = API(companion)
    sensors = [Cpu, Memory, Uptime]
    api.register_device()
    [api.register_sensor(s) for s in sensors]
    while True:
        sleep(5)
        api.update_sensors(sensors)


main()
