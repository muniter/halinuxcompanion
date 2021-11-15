from halinuxcompanion.api import API, Server
from halinuxcompanion.dbus import init_bus
from halinuxcompanion.notifier import Notifier
from halinuxcompanion.companion import Companion
from halinuxcompanion.sensors.cpu import Cpu
from halinuxcompanion.sensors.memory import Memory
from halinuxcompanion.sensors.uptime import Uptime

import asyncio
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
        logger.critical("Config file not found %s, exiting now", file)
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
        # DBus session client to send desktop notifications and listen to signals
        bus = await init_bus()
        # Notifier HA -> Webserver -> dbus | dbus -> event_handler -> HA
        notifier = Notifier()
        await notifier.init(bus, api, server, companion.app_data["push_token"], companion.url_program)
        await server.start()

    # If the device can't be registered exit immidiately, nothing to do.
    if not await api.register_companion():
        logger.critical("Device registration failed, exiting now")
        exit(1)

    # TODO: Errors in sensor registration should exit the program, currently unhandled exception
    await asyncio.gather(*[api.register_sensor(s) for s in sensors])
    await api.update_sensors(sensors)  # Send initial data to Home Assistant (again, needed)

    interval = companion.refresh_interval
    # Loop forever updating sensors.
    while True:
        await asyncio.sleep(interval)
        await api.update_sensors(sensors)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
