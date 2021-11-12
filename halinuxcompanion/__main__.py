from halinuxcompanion.api import API
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
    global logger
    if args.loglevel != "":
        logger.setLevel(args.loglevel)
    elif "loglevel" in config:
        logger.setLevel(config["loglevel"])

    companion = Companion(config)
    async with aiohttp.ClientSession() as session:
        api = API(companion, session)
        sensors = [Cpu, Memory, Uptime]
        await api.register_device()
        await asyncio.gather(*[api.register_sensor(s) for s in sensors])
        interval = companion.refresh_interval
        # TODO: Catch network problems.
        while True:
            await asyncio.sleep(interval)
            await api.update_sensors(sensors)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
