from halinuxcompanion.api import Server
from halinuxcompanion.notifier import Notifier
from halinuxcompanion.sensors.status import Status
import json
from halinuxcompanion.companion import CommandConfig, Companion
import pytest


def get_config() -> dict:
    with open("tests/config.json") as f:
        data = json.load(f)
        return data


class RequestStub:
    def __init__(self, json):
        self.__json = json

    async def json(self):
        return self.__json


def setup_companion() -> Companion:
    data = get_config()
    companion = Companion(data)
    return companion


def setup_notifier() -> Notifier:
    notifier = Notifier()
    return notifier


def test_status_updater():
    Status.updater()


@pytest.mark.asyncio
async def test_notifier():
    notifier = setup_notifier()
    notifier.push_token = "d0f7bd90-7b23-11ee-852f-0 0d861ab3a9c"
    notifier.commands = {
        "command_suspend": CommandConfig(name="Suspend", command=["ls"]),
    }

    # Existing command
    payload = {
        "message": "command_suspend",
        "push_token": notifier.push_token,
        "registration_info": {
            "app_id": "Linux_Companion0.0.1",
            "app_version": "0.0.1",
            "webhook_id": "fd0e8af0183a1445e029436995286479a57d5a455b4d6ce3e40b743c3969b 505",
            "os_version": "6.5.9-arch2-1",
        },
    }
    result = await notifier.on_ha_notification(RequestStub(payload))
    assert result is not None

    # Non existing command
    payload = {
        "message": "suspend",
        "push_token": notifier.push_token,
        "registration_info": {
            "app_id": "Linux_Companion0.0.1",
            "app_version": "0.0.1",
            "webhook_id": "fd0e8af0183a1445e029436995286479a57d5a455b4d6ce3e40b743c3969b 505",
            "os_version": "6.5.9-arch2-1",
        },
    }
    result = await notifier.on_ha_notification(RequestStub(payload))
    assert result is not None


def test_setup():
    assert True


def test_companion_init():
    companion = setup_companion()
    assert companion is not None
