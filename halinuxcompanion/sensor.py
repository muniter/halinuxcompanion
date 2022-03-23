from halinuxcompanion.api import API
from halinuxcompanion.dbus import Dbus
from aiohttp import ClientError
from typing import Union, List, Dict, Callable
from functools import partial
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

SC_REGISTER_SENSOR = 301


class Sensor:
    """Standard sensor class"""
    instances = []

    def __init__(self):
        self.config_name: str
        self.attributes: dict = {}
        self.device_class: str = ""
        self.state_class: str = ""
        self.icon: str
        self.name: str
        self.state: Union[str, int, float] = ""
        self.type: str
        self.unique_id: str
        self.unit_of_measurement: str = ""
        self.state_class: str = ""
        self.entity_category: str = ""
        self.type: str
        # Signal name (halinuxcompanion.dbus) and it's callback
        self.signals: Dict[str, Callable] = {}
        Sensor.instances.append(self)

    # TODO: Should be async
    def updater(self) -> None:
        """To be called every time update is called"""
        pass

    def update(self) -> dict:
        """Payload to update the sensor"""
        self.updater()
        return {
            "attributes": self.attributes,
            "icon": self.icon,
            "state": self.state,
            "type": self.type,
            "unique_id": self.unique_id,
        }

    def register(self) -> dict:
        self.updater()
        """Payload to register the sensor"""
        data = {
            "attributes": self.attributes,
            "device_class": self.device_class,
            "icon": self.icon,
            "name": self.name,
            "state": self.state,
            "type": self.type,
            "unique_id": self.unique_id,
            "unit_of_measurement": self.unit_of_measurement,
            "state_class": self.state_class,
            "entity_category": self.entity_category,
        }
        pop = []
        for key in data:
            if data[key] == "":
                pop.append(key)
        [data.pop(key) for key in pop]
        return data

    def update(self) -> dict:
        """Payload to update the sensor"""
        self.updater()
        return {
            "attributes": self.attributes,
            "icon": self.icon,
            "state": self.state,
            "type": self.type,
            "unique_id": self.unique_id,
        }


class SensorManager:
    """Manages sensors registration, and updates to Home Assistant"""
    api: API
    update_counter: int = 0
    sensors: List[Sensor] = []
    dbus: Dbus

    def __init__(self, api: API, sensors: List[Sensor], dbus: Dbus) -> None:
        self.api = api
        self.sensors = sensors
        self.dbus = dbus

    async def register_sensors(self) -> bool:
        """Register all sensors with Home Assisntat
        If all have been registered successfully, register each sensor signals
        """
        res = await asyncio.gather(*[self._register_sensor(s) for s in self.sensors])
        if all(res):
            # If all sensors registered successfully, register their signals
            await self.register_signals()
            return True

        return False

    async def _register_sensor(self, sensor: Sensor) -> bool:
        """Register a sensor with Home Assisntat
        If the registration fails it's a critical error and the program should exit.

        :param sensor: The sensor to register
        :return: True if the registration was successful, False otherwise
        """
        data = {"data": sensor.register(), "type": "register_sensor"}
        sid = sensor.unique_id
        data = json.dumps(data)
        logger.info('Registering sensor:%s payload:%s', sid, data)
        res = await self.api.webhook_post('register_sensor', data=data)

        if res.ok or res.status == SC_REGISTER_SENSOR:
            logger.info('Sensor registration successful: %s', sid)
            return True
        else:
            logger.error('Sensor registration failed with status code:%s sensor:%s', res.status, sid)
            return False

    async def update_sensors(self, sensors: List[Sensor] = []) -> bool:
        """Update the given sensors with Home Assisntat
        If the update fails it's an error and it should be retried by the caller.

        :param sensors: The sensors to update, if empty all sensors will be updated
        :return: True if the update was successful, False otherwise
        """
        sensors = sensors or self.sensors
        self.update_counter += 1
        data = {"type": "update_sensor_states", "data": [sensor.update() for sensor in sensors]}
        snames = [sensor.config_name for sensor in sensors]
        logger.info('Sensors update %s with sensors: %s', self.update_counter, snames)
        logger.debug('Sensors update %s with sensors: %s payload: %s', self.update_counter, snames, data)
        try:
            res = await self.api.webhook_post('update_sensors', data=json.dumps(data))
            if res.ok or res.status == SC_REGISTER_SENSOR:
                logger.info('Sensors update %s successful', self.update_counter)
                return True
            else:
                logger.error('Sensors update %s failed with status code:%s', self.update_counter, res.status)
        except ClientError as e:
            logger.error('Sensors update %s failed with error:%s', self.update_counter, e)

        return False

    async def _signal_hanlder(self, sensor: Sensor, signal_alias: str, signal_handler: Callable, *args) -> None:
        """Signal handler for the sensor manager
        Each sensor can have multiple signals, at the moment defined in halinuxcompanion.dbus, the callback provided for
        the signal is this function wrapped in a functools.partial this allows for the SensorManager to be in charge of
        actually calling the sensor callback and therefore be able to know when to update it.

        :param sensor: The sensor that the signal belongs to
        :param signal_alias: The signal alias (defined in halinuxcompanion.dbus)
        :param signal_handler: The signal handler (defined by the sensor in sensor.signals)
        :param args: The arguments to pass to the signal handler (coming from the dbus signal)
        """
        logger.info('Signal %s received for sensor:%s', signal_alias, sensor.unique_id)
        await signal_handler(sensor, *args)
        await self.update_sensors([sensor])

    async def register_signals(self) -> None:
        """Register all signals from all sensors.
        Each sensor defines signals with a name and callback, which is called by self._signal_handler
        """
        for sensor in self.sensors:
            for signal_alias, signal_handler in sensor.signals.items():
                callback = partial(self._signal_hanlder, sensor, signal_alias, signal_handler)
                await self.dbus.register_signal(signal_alias, callback)
