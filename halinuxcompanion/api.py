from .companion import Companion
from .sensor import Sensor

import json
import logging
from aiohttp import (web, ClientSession, ClientResponse, ClientError)
from typing import List, Union

logger = logging.getLogger(__name__)

SC_OK = 200
SC_REGISTER_SENSOR = 301
SC_INVALID_JSON = 400
SC_MOBILE_COMPONENT_NOT_LOADED = 404
SC_INTEGRATION_DELETED = 410
SESSION: Union[ClientSession, None] = None


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
    update_counter: int = 0
    session: ClientSession

    def __init__(self, companion: Companion):
        global SESSION
        if SESSION is None:
            SESSION = ClientSession()
        self.session = SESSION
        self.token = companion.ha_token
        self.headers = {'Authorization': 'Bearer ' + self.token}
        self.instance_url = companion.ha_url
        self.register_payload = companion.registration_payload()

    async def webhook_post(self, type: str, data: str) -> ClientResponse:
        """Send a POST request to the webhook endpoint with the given type and data
        Simple wrapper that handles and logs response status, should be wrapped to handle clinet errors.
        :param type: Whats being posted, ussed for logging
        :param data: The data to send in the body of the request (json serialized)
        """

        logger.debug('Sending webhook POST %s type:%s ', self.counter, type)

        async with self.session.post(self.webhook_url, data=data) as res:
            logger.debug('Recived response %s to request %s', res.status, self.counter)
            self.counter += 1

            if logger.level == logging.DEBUG:
                if res.status == SC_INVALID_JSON:
                    logger.error('Invalid JSON %s', self.webhook_url)
                if res.status == SC_MOBILE_COMPONENT_NOT_LOADED:
                    logger.error('The mobile_app component has not ben loaded %s', self.webhook_url)
                elif res.status == SC_INTEGRATION_DELETED:
                    logger.error('The integration has been deleted, need to register again %s', self.webhook_url)

            return res

    async def post(self, endpoint: str, data: str) -> ClientResponse:
        """Send a POST request to the given Home Assisntat endpoint
        Headers are set to the token and the body is set to the data

        :param endpoint: The endpoint to send the request to (must have a leading /)
        :param data: The data to send in the body of the request (json serialized)
        :return: The response from Home Assisntat
        """
        return await self.session.post(self.instance_url + endpoint, headers=self.headers, data=data)

    async def get(self, endpoint: str) -> ClientResponse:
        """Send a GET request to the given Home Assisntat endpoint
        Headers are set to the token

        :param endpoint: The endpoint to send the request to (must have a leading /)
        :return: The response from Home Assisntat
        """
        return await self.session.get(self.instance_url + endpoint, headers=self.headers)

    async def register_companion(self) -> bool:
        """Register the companion with Home Assisntat
        If the registration fails it's a critical error and the program should exit.

        :return: True if the registration was successful, False otherwise
        """
        register_data = json.dumps(self.register_payload)
        logger.info('Registering companion device with payload:%s', register_data)
        res = await self.post('/api/mobile_app/registrations', data=register_data)

        if res.ok:
            data = await res.json()
            self.cloudhook_url = data.get('cloudhook_url', None)
            self.remote_ui_url = data.get('remote_ui_url', None)
            # Both should error if not present
            self.secret = data['secret']
            self.webhook_id = data['webhook_id']
            self.webhook_url = self.instance_url + '/api/webhook/' + self.webhook_id
            logger.info('Device Registration successful, received the neccesarry data from the server')
            return True
        else:
            logger.critical('Device Registration failed with status code %s', res.status)
            return False

    async def register_sensor(self, sensor: Sensor):
        """Register a sensor with Home Assisntat
        If the registration fails it's a critical error and the program should exit.

        :param sensor: The sensor to register
        :return: True if the registration was successful, False otherwise
        """
        data = {"data": sensor.register(), "type": "register_sensor"}
        sid = sensor.unique_id
        data = json.dumps(data)
        logger.info('Registering sensor:%s payload:%s', sid, data)
        res = await self.webhook_post('register_sensor', data=data)

        if res.ok or res.status == SC_REGISTER_SENSOR:
            logger.info('Sensor registration successful: %s', sid)
            return True
        else:
            logger.error('Sensor registration failed with status code:%s sensor:%s', res.status, sid)
            return False

    async def update_sensors(self, sensors: List[Sensor]) -> bool:
        """Update the given sensors with Home Assisntat
        If the update fails it's an error and it should be retried by the caller.

        :param sensors: The sensors to update
        :return: True if the update was successful, False otherwise
        """
        self.update_counter += 1
        data = {"type": "update_sensor_states", "data": [sensor.update() for sensor in sensors]}
        sids = [sensor.unique_id for sensor in sensors]
        logger.info('Sensors update %s with sensors: %s', self.update_counter, sids)
        try:
            res = await self.webhook_post('update_sensors', data=json.dumps(data))
            if res.ok or res.status == SC_REGISTER_SENSOR:
                logger.info('Sensors update %s successful', self.update_counter)
                return True
            else:
                logger.error('Sensors update %s failed with status code:%s', self.update_counter, res.status)
        except ClientError as e:
            logger.error('Sensors update %s failed with error:%s', self.update_counter, e)

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
