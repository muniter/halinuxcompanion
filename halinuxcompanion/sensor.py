from typing import Union

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
            "type": self.type
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

class DeviceTracker:
    pass
