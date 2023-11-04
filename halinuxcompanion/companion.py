import json
import platform
import uuid
import logging
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from halinuxcompanion.api import API

CONFIG_KEYS = [
    ("ha_url", True),
    ("ha_token", True),
    ("device_id", True),
    ("device_name", False),
    ("manufacturer", False),
    ("model", False),
    ("computer_ip", True),
    ("computer_port", True),
    ("refresh_interval", False),
    ("services", True),
    ("sensors", True),
]


class CommandConfig(BaseModel):
    name: str
    command: List[str]


class NotificationServiceConfig(BaseModel):
    enabled: bool
    url_program: str
    commands: Dict[str, CommandConfig]


class ServicesConfig(BaseModel):
    notifications: Optional[NotificationServiceConfig]


class SensorConfig(BaseModel):
    enabled: bool
    name: str


class CompanionConfig(BaseModel):
    ha_url: str
    ha_token: str
    device_id: str
    device_name: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    computer_ip: str
    computer_port: int
    refresh_interval: Optional[int]
    sensors: Dict[str, SensorConfig]
    services: Optional[ServicesConfig]


logger = logging.getLogger("halinuxcompanion")


class Companion:
    """Class encolsing a companion instance
    https://developers.home-assistant.io/docs/api/native-app-integration/setup
    """

    # TODO: This class is just a huge pile of things
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
    encryption_key: str = "NOT IMPLEMENTED"
    supports_encryption: bool = False
    app_data: dict = {}
    notifier: bool = False
    refresh_interval: int = 15
    computer_ip: str = ""
    computer_port: int = 8400
    ha_url: str = "http://localhost:8123"
    ha_token: str
    url_program: str = ""
    commands: Dict[str, CommandConfig] = {}
    sensors: Dict[str, bool] = {}

    def __init__(self, config: dict):
        # Load only allowed values
        parsed = CompanionConfig.model_validate(config)
        self.load_config_from_model(parsed)

    def load_config_from_model(self, config: CompanionConfig):
        self.ha_url = config.ha_url.rstrip("/")
        self.ha_token = config.ha_token
        self.device_id = config.device_id
        self.device_name = config.device_name if config.device_name else self.device_name
        self.manufacturer = config.manufacturer if config.manufacturer else self.manufacturer
        self.model = config.model if config.model else self.model
        self.computer_ip = config.computer_ip
        self.computer_port = config.computer_port
        self.refresh_interval = config.refresh_interval if config.refresh_interval else self.refresh_interval

        from halinuxcompanion.sensors import __all__ as all_sensors
        for name, sensor in config.sensors.items():
            if name not in all_sensors:
                logger.error("Sensor %s doesn't exist", name)
                exit(1)
            else:
                self.sensors[name] = sensor.enabled

        if config.services and config.services.notifications and config.services.notifications.enabled:
            self.notifier = True
            self.app_data = {
                "push_token": str(uuid.uuid1()),  # TODO: Random generation
                "push_url": f"http://{self.computer_ip}:{self.computer_port}/notify",
            }
            self.url_program = config.services.notifications.url_program
            self.commands = config.services.notifications.commands

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

    async def register(self, api: "API") -> Tuple[bool, dict]:
        """Register the companion with Home Assisntat
        If the registration fails it's a critical error and the program should exit.

        :return: (True, registration_data) if successful, (False, {}) otherwise
        """
        register_data = json.dumps(self.registration_payload())
        logger.info("Registering companion device with payload:%s", register_data)
        res = await api.post("/api/mobile_app/registrations", data=register_data)

        if res.ok:
            logger.info("Device Registration successful")
            data = await res.json()
            return True, data
        else:
            text = await res.text()
            logger.critical(
                "Device Registration failed with status code %s, text: %s",
                res.status,
                text,
            )
            return False, {}
