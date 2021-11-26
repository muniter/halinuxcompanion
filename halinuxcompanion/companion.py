import json
import platform
import uuid
import logging
from typing import Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from halinuxcompanion.api import API


logger = logging.getLogger("halinuxcompanion")

CONFIG_KEYS = [("ha_url", True), ("ha_token", True), ("device_id", True), ("device_name", False),
               ("manufacturer", False), ("model", False), ("computer_ip", True), ("computer_port", True),
               ("refresh_interval", False), ("services", True)]


class Companion:
    """Class encolsing a companion instance
    https://developers.home-assistant.io/docs/api/native-app-integration/setup
    """
    # TODO: Revisit this device_id which must be unique, used for notification events
    device_id: str = platform.node()
    # TODO: Get the default values from something that helps sets releases.
    app_name: str = "Linux Companion"
    app_version: str = "0.0.1"
    app_id: str = app_name.replace(" ", "_") + app_version
    device_name: str = platform.node()
    manufacturer: str = platform.system()
    model: str = "Computer"
    os_name: str = platform.system()
    os_version: str = platform.release()
    # TODO: Encryption requires https://github.com/jedisct1/libsodium
    supports_encryption: bool = False
    app_data: dict = {}
    notifier: bool = False
    refresh_interval: int = 15
    computer_ip: str = ""
    computer_port: int = 8400
    ha_url: str = "http://localhost:8123"
    ha_token: str
    url_program: str = ""
    commands: Dict[str, dict] = {}

    def __init__(self, config: dict):
        # Load only allowed values
        for key, req in CONFIG_KEYS:
            value = config.get(key, None)
            if value is None and req:
                raise ValueError(f"Missing required config key: {key}")
            else:
                # Set only for none empty values
                if value != "":
                    setattr(self, key, value)

            # Enable notificaions
            try:
                # TODO: This validation is very flacky, solve it by providing a default dict
                if config["services"]["notifications"]["enabled"] is True:
                    self.notifier = True
                    self.app_data = {
                        "push_token": str(uuid.uuid1()),  # TODO: Random generation
                        "push_url": f"http://{self.computer_ip}:{self.computer_port}/notify",
                    }
                    self.url_program = config["services"]["notifications"].get("url_program", "")
                    self.commands = config["services"]["notifications"].get("commands", {})
            except KeyError:
                pass

            # Cleanup some of the values
            self.ha_url = self.ha_url.rstrip("/")

    def registration_payload(self) -> dict:
        return {
            "device_id": self.device_id,
            "app_id": self.app_id,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "device_name": self.device_name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "supports_encryption": self.supports_encryption,
            "app_data": self.app_data,
        }

    async def register(self, api: 'API') -> Tuple[bool, dict]:
        """Register the companion with Home Assisntat
        If the registration fails it's a critical error and the program should exit.

        :return: (True, registration_data) if successful, (False, {}) otherwise
        """
        register_data = json.dumps(self.registration_payload())
        logger.info('Registering companion device with payload:%s', register_data)
        res = await api.post('/api/mobile_app/registrations', data=register_data)

        if res.ok:
            logger.info('Device Registration successful')
            data = await res.json()
            return True, data
        else:
            logger.critical('Device Registration failed with status code %s', res.status)
            return False, {}
