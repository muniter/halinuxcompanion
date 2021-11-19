from halinuxcompanion.api import API, Server
from halinuxcompanion.dbus import Dbus
from halinuxcompanion.notifier import Notifier
from halinuxcompanion.sensor import SensorManager
from halinuxcompanion.companion import Companion
from halinuxcompanion.sensors.cpu import Cpu
from halinuxcompanion.sensors.memory import Memory
from halinuxcompanion.sensors.uptime import Uptime
from halinuxcompanion.sensors.status import Status

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
    """ Main function
    The program is fairly simple, data is sent and received to/from Home Assistant over HTTP
    Sensors:
        - Data is collected from sensors and sent to Home Assistant.
    Notifications:
        - Sent from Home Assistant to the application via embeded webserver, this are sent to the desktop using Dbus.
        - Actions are triggered in dbus listened by the application. Some are handled locally others are handled by Home
          Assistant, events are relayed to it as expected (closed and action).
    """
    args = commandline()
    logging.basicConfig(level="INFO")
    config = load_config(args.config)

    # Command line loglevel takes precedence
    if args.loglevel != "":
        logger.setLevel(args.loglevel)
    elif "loglevel" in config:
        logger.setLevel(config["loglevel"])

    companion = Companion(config)  # Companion objet where configuration is stored
    api = API(companion)  # API client to send data to Home Assistant
    server = Server(companion)  # HTTP server that handles notifications
    # Initialize dbus connections
    bus = Dbus()
    await bus.init()
    # Register sensors
    sensor_manager = SensorManager(api, [Cpu, Memory, Uptime, Status], bus)

    # If the device can't be registered exit immidiately, nothing to do.
    ok, reg_data = await companion.register(api)
    api.process_registration_data(reg_data)
    if not ok:
        logger.critical("Device registration failed, exiting now")
        exit(1)

    # If sensors can't be registered exit immidiately, nothing to do.
    if not await sensor_manager.register_sensors():
        logger.critical("Sensor registration failed, exiting now")
        exit(1)

    # Initialize the notifier which implies the webserver and the dbus interface
    if companion.notifier:
        # TODO: Session bus is initialized already.
        # DBus session client to send desktop notifications and listen to signals
        # Notifier behavior: HA -> Webserver -> dbus ... dbus -> event_handler -> HA
        notifier = Notifier()
        await notifier.init(bus, api, server, companion.app_data["push_token"], companion.url_program)
        await server.start()

    interval = companion.refresh_interval
    # Loop forever updating sensors.
    while True:
        await sensor_manager.update_sensors()
        await asyncio.sleep(interval)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
