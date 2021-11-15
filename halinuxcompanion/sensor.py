from halinuxcompanion.api import API
from aiohttp import ClientError
from typing import Union, List
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

SC_REGISTER_SENSOR = 301


class Sensor:
    """Standard sensor class"""
    attributes: dict = {}
    device_class: str = ""
    icon: str
    name: str
    state: Union[str, int, float] = ""
    type: str
    unique_id: str
    unit_of_measurement: str = ""
    state_class: str = ""
    entity_category: str = ""
    type: str

    def updater(self) -> None:
        """To be called every time update is called"""
        pass

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

    def __init__(self, api: API, sensors: List[Sensor]) -> None:
        self.api = api
        self.sensors = sensors

    async def register_sensors(self) -> bool:
        """Register all sensors with Home Assisntat"""
        res = await asyncio.gather(*[self._register_sensor(s) for s in self.sensors])
        return all(res)

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
        sids = [sensor.unique_id for sensor in sensors]
        logger.info('Sensors update %s with sensors: %s', self.update_counter, sids)
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
