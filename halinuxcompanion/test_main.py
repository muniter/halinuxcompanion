from halinuxcompanion.sensors.status import Status
import json
from halinuxcompanion.companion import Companion


def get_config() -> dict:
    with open("tests/config.json") as f:
        data = json.load(f)
        return data


def setup_companion() -> Companion:
    data = get_config()
    companion = Companion(data)
    return companion


def test_status_updater():
    Status.updater()


def test_setup():
    assert True


def test_companion_init():
    companion = setup_companion()
    assert companion is not None
