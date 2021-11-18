from .companion import Companion

import logging
from aiohttp import (web, ClientSession, ClientResponse)
from typing import Union

logger = logging.getLogger(__name__)

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
    session: ClientSession

    def __init__(self, companion: Companion) -> None:
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

        self.counter += 1
        logger.debug('Sending webhook POST %s type:%s ', self.counter, type)

        async with self.session.post(self.webhook_url, data=data) as res:
            logger.debug('Recived response %s to request %s', res.status, self.counter)

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

    def process_registration_data(self, data: dict) -> None:
        """Process the data returned from the registration endpoint
        :param data: The data returned from the registration endpoint
        """
        self.secret = data['secret']
        self.webhook_id = data['webhook_id']
        self.webhook_url = self.instance_url + '/api/webhook/' + self.webhook_id
        self.cloudhook_url = data.get('cloudhook_url', "")
        self.remote_ui_url = data.get('remote_ui_url', "")


class Server:
    """Class that runs an http server and handles requests in the route /notify"""
    app: web.Application
    host: str
    port: int

    def __init__(self, companion: Companion) -> None:
        self.app = web.Application()
        self.host = companion.computer_ip
        self.port = companion.computer_port

    async def start(self) -> None:
        logger.info('Starting http server on %s:%s', self.host, self.port)
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info('Server started on %s:%s', self.host, self.port)
