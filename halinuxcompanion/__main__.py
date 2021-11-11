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
logger = logging.getLogger("halinuxcompanion")


def load_config(file="config.json") -> dict:
    logger.info(f"Reading configuration file {file}")
    try:
        with open(file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found {file}")
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
        default="",
    )
    args = parser.parse_args()
    return args


def main():
    args = commandline()
    logging.basicConfig(level="INFO")
    config = load_config(args.config)

    # Command line loglevel takes precedence
    global logger
    if args.loglevel != "":
        logger.setLevel(args.loglevel)
    elif "loglevel" in config:
        logger.setLevel(config["loglevel"])

    companion = Companion(config)
    api = API(companion)
    sensors = [Cpu, Memory, Uptime]
    api.register_device()
    [api.register_sensor(s) for s in sensors]
    interval = companion.refresh_interval
    # TODO: Catch network problems.
    # TODO: Move to asyncronous requests
    # TODO: Move to asyncronous loop
    while True:
        sleep(interval)
        api.update_sensors(sensors)


main()
