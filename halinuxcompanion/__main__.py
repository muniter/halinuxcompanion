from halinuxcompanion.api import API, Server
from halinuxcompanion.dbus import init_bus
from halinuxcompanion.notifier import Notifier
from halinuxcompanion.companion import Companion
from halinuxcompanion.sensors.cpu import Cpu
from halinuxcompanion.sensors.memory import Memory
from halinuxcompanion.sensors.uptime import Uptime

import asyncio
import aiohttp
import json
import logging
import argparse
# set logging level using and environment variable
logger = logging.getLogger("halinuxcompanion")


def load_config(file="config.json") -> dict:
    logger.info("Reading configuration file %s", file)
    try:
        with open(file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Config file not found %s", file)
        exit(1)


def commandline() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Home Assistan Linux Companion")
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


async def main():
    args = commandline()
    logging.basicConfig(level="INFO")
    config = load_config(args.config)

    # Command line loglevel takes precedence
    if args.loglevel != "":
        logger.setLevel(args.loglevel)
    elif "loglevel" in config:
        logger.setLevel(config["loglevel"])

    companion = Companion(config)
    api = API(companion)  # API client to send data to Home Assistant
    server = Server(companion)  # HTTP server that handles notifications
    sensors = [Cpu, Memory, Uptime]  # Sensors to send to Home Assistant

    if companion.notifier:
        bus = await init_bus()  # DBus client to send desktop notifications and listen to signals
        notifier = Notifier()  # Notifier that handles from server and sends to bus
        await notifier.init(bus, server)

    await api.register_device()
    await asyncio.gather(*[api.register_sensor(s) for s in sensors])
    # This might also fit in gather as taks
    await server.start()

    interval = companion.refresh_interval
    # TODO: Catch network problems.
    while True:
        await asyncio.sleep(interval)
        await api.update_sensors(sensors)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
