from .companion import Companion
from .sensor import Sensor

import aiohttp
import json
from typing import List
import logging

logger = logging.getLogger(__name__)

SC_OK = 200
SC_REGISTER_SENSOR = 301
SC_INVALID_JSON = 400
SC_MOBILE_COMPONENT_NOT_LOADED = 404
SC_INTEGRATION_DELETED = 410


class API:
    instance_url: str
    token: str
    headers: dict
    register_payload: dict
    # Returned by register_device
    cloudhook_url: str or None
    remote_ui_url: str or None
    secret: str
    webhook_id: str
    webhook_url: str
    counter: int = 0
    session: aiohttp.ClientSession

    def __init__(self, companion: Companion, session: aiohttp.ClientSession):
        self.session = session
        self.token = companion.ha_token
        self.headers = {'Authorization': 'Bearer ' + self.token}
        self.instance_url = companion.ha_url
        self.register_payload = companion.registration_payload()

    async def webhook_request(self, type: str, data: str) -> aiohttp.ClientResponse:
        logger.debug(f'Sending request {self.counter} to {self.webhook_url} json:{data}')
        logger.info(f'Sending webhook request {self.counter} type:{type}')

        async with self.session.post(self.webhook_url, data=data) as res:
            logger.info(f'Recived response {res.status} to request {self.counter}')
            self.counter += 1

            if logger.level == logging.DEBUG:
                if res.status == SC_INVALID_JSON:
                    logger.error(f'Invalid JSON {self.webhook_url}')
                if res.status == SC_MOBILE_COMPONENT_NOT_LOADED:
                    logger.error(f'The mobile_app component has not ben loaded {self.webhook_url}')
                elif res.status == SC_INTEGRATION_DELETED:
                    logger.error(f'The integration has been deleted, need to register again {self.webhook_url}')

            return res

    async def register_device(self):
        logger.info(f'Registering companion device with payload:{self.register_payload}')
        async with self.session.post(self.instance_url + '/api/mobile_app/registrations',
                                     headers=self.headers,
                                     data=json.dumps(self.register_payload)) as res:

            if res.ok:
                data = await res.json()
                self.cloudhook_url = data.get('cloudhook_url', None)
                self.remote_ui_url = data.get('remote_ui_url', None)
                # Both should error if not present
                self.secret = data['secret']
                self.webhook_id = data['webhook_id']
                self.webhook_url = self.instance_url + '/api/webhook/' + self.webhook_id
                logger.info('Registration successful, received the neccesarry data from the server')
                logger.debug(f'Registration data received {data}')
                return True
            else:
                logger.error(f'Registration failed with status code {res.status}')
                return False

    async def register_sensor(self, sensor: Sensor):
        data = {"data": sensor.register(), "type": "register_sensor"}
        sid = sensor.unique_id
        data = json.dumps(data)
        logger.info(f'Registering sensor:{sid} payload:{data}')
        res = await self.webhook_request('register_sensor', data=data)

        if res.ok or res.status == SC_REGISTER_SENSOR:
            logger.info(f'Sensor registration successful: {sid}')
            # Seems like home assistant needs and update after registering a sensor
            # to reflect the value of the sensor state.
            return True
        else:
            logger.error(f'Sensor registration failed with status code:{res.status} sensor:{sid}')
            return False

    async def update_sensors(self, sensors: List[Sensor]):
        data = {"type": "update_sensor_states", "data": [sensor.update() for sensor in sensors]}
        sids = [sensor.unique_id for sensor in sensors]
        logger.info(f'Updating sensors with id:{sids}')
        res = await self.webhook_request('register_sensor', data=json.dumps(data))

        if res.ok or res.status == SC_REGISTER_SENSOR:
            logger.info(f'Sensor update successful: {sids}')
            return True
        else:
            logger.error(f'Sensor update failed with status code:{res.status} sensors:{sids}')
            return False
