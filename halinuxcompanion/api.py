from .companion import Companion
from .sensor import Sensor

import aiohttp
from aiohttp import web
import json
from typing import List, Union
import logging

logger = logging.getLogger(__name__)

SC_OK = 200
SC_REGISTER_SENSOR = 301
SC_INVALID_JSON = 400
SC_MOBILE_COMPONENT_NOT_LOADED = 404
SC_INTEGRATION_DELETED = 410
SESSION: Union[aiohttp.ClientSession, None] = None


class API:
    """Class that handles Home Assisntat HTTP API calls"""
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

    def __init__(self, companion: Companion):
        global SESSION
        if SESSION is None:
            SESSION = aiohttp.ClientSession()
        self.session = SESSION
        self.token = companion.ha_token
        self.headers = {'Authorization': 'Bearer ' + self.token}
        self.instance_url = companion.ha_url
        self.register_payload = companion.registration_payload()

    async def webhook_request(self, type: str, data: str) -> aiohttp.ClientResponse:

        logger.debug('Sending request %s json:%s', self.webhook_url, data)
        logger.info('Sending webhook request %s type:%s', self.counter, type)

        async with self.session.post(self.webhook_url, data=data) as res:
            logger.info('Recived response %s to request %s', res.status, self.counter)
            self.counter += 1

            if logger.level == logging.DEBUG:
                if res.status == SC_INVALID_JSON:
                    logger.error('Invalid JSON %s', self.webhook_url)
                if res.status == SC_MOBILE_COMPONENT_NOT_LOADED:
                    logger.error('The mobile_app component has not ben loaded %s', self.webhook_url)
                elif res.status == SC_INTEGRATION_DELETED:
                    logger.error('The integration has been deleted, need to register again %s', self.webhook_url)

            return res

    async def register_device(self):
        logger.info('Registering companion device with payload:%s', self.register_payload)
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
                logger.debug('Registration data received %s', data)
                return True
            else:
                logger.error('Registration failed with status code %s', res.status)
                return False

    async def register_sensor(self, sensor: Sensor):
        data = {"data": sensor.register(), "type": "register_sensor"}
        sid = sensor.unique_id
        data = json.dumps(data)
        logger.info('Registering sensor:%s payload:%s', sid, data)
        res = await self.webhook_request('register_sensor', data=data)

        if res.ok or res.status == SC_REGISTER_SENSOR:
            logger.info('Sensor registration successful: %s', sid)
            # Seems like home assistant needs and update after registering a sensor
            # to reflect the value of the sensor state.
            return True
        else:
            logger.error('Sensor registration failed with status code:%s sensor:%s', res.status, sid)
            return False

    async def update_sensors(self, sensors: List[Sensor]):
        data = {"type": "update_sensor_states", "data": [sensor.update() for sensor in sensors]}
        sids = [sensor.unique_id for sensor in sensors]
        logger.info('Updating sensors with id:%s', sids)
        res = await self.webhook_request('register_sensor', data=json.dumps(data))

        if res.ok or res.status == SC_REGISTER_SENSOR:
            logger.info('Sensor update successful: %s', sids)
            return True
        else:
            logger.error('Sensor update failed with status code:%s sensors:%s', res.status, sids)
            return False


class Server:
    """Class that runs an http server and handles requests in the route /notify"""
    app: web.Application
    host: str
    port: int

    def __init__(self, companion: Companion):
        self.app = web.Application()
        self.host = companion.computer_ip
        self.port = companion.computer_port

    async def start(self):
        logger.info('Starting http server on %s:%s', self.host, self.port)
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info('Server started on %s:%s', self.host, self.port)
