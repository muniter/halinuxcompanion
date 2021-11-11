from halinuxcompanion.api import API
from halinuxcompanion.companion import Companion
from halinuxcompanion.sensors.cpu import Cpu
from halinuxcompanion.sensors.memory import Memory
from halinuxcompanion.sensors.uptime import Uptime

from time import sleep
import json
import logging
import argparse
# set logging level using and environment variable
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(file="config.json") -> dict:
    try:
        with open(file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Config file not found " + file)
        exit(1)


def commandline() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Home Assistan Linux Companion")
    parser.add_argument(
        "-c",
        "--config",
        help="Path to config file",
        default="config.json",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        help="Log level",
        default="INFO",
    )
    args = parser.parse_args()
    return args


def main():
    args = commandline()
    logger.setLevel(args.loglevel)
    logger.info("Reading configuration file")
    config = load_config()
    companion = Companion(config)
    api = API(companion)
    sensors = [Cpu, Memory, Uptime]
    api.register_device()
    [api.register_sensor(s) for s in sensors]
    interval = companion.refresh_interval
    while True:
        sleep(interval)
        api.update_sensors(sensors)


main()
