from dbus_next.aio import MessageBus, ProxyInterface
from dbus_next import BusType
from typing import Callable
import logging

logger = logging.getLogger(__name__)

SIGNALS = {
    "session.notification_on_action_invoked": {
        "name": "on_action_invoked",
        "interface": "org.freedesktop.Notifications",
    },
    "session.notification_on_notification_closed": {
        "name": "on_notification_closed",
        "interface": "org.freedesktop.Notifications",
    },
    "system.login_on_prepare_for_sleep": {
        "name": "on_prepare_for_sleep",
        "interface": "org.freedesktop.login1.Manager",
    },
    "system.login_on_prepare_for_shutdown": {
        "name": "on_prepare_for_shutdown",
        "interface": "org.freedesktop.login1.Manager",
    },
    "subscribed": [],
}

INTERFACES = {
    "org.freedesktop.login1.Manager": {
        "type": "system",
        "service": "org.freedesktop.login1",
        "path": "/org/freedesktop/login1",
        "interface": "org.freedesktop.login1.Manager",
    },
    "org.freedesktop.Notifications": {
        "type": "session",
        "service": "org.freedesktop.Notifications",
        "path": "/org/freedesktop/Notifications",
        "interface": "org.freedesktop.Notifications",
    },
}


async def get_interface(bus, service, path, interface) -> ProxyInterface:
    introspection = await bus.introspect(service, path)
    proxy = bus.get_proxy_object(service, path, introspection)
    return proxy.get_interface(interface)


class Dbus:
    session: MessageBus
    system: MessageBus
    interfaces: dict[str, ProxyInterface] = {}

    async def init(self) -> None:
        self.system = await MessageBus(bus_type=BusType.SYSTEM).connect()
        self.session = await MessageBus(bus_type=BusType.SESSION).connect()

    async def get_interface(self, name: str) -> ProxyInterface:
        i = INTERFACES[name]
        bus_type, service, path, interface = i["type"], i["service"], i["path"], i["interface"]
        iface = self.interfaces.get(name)
        if iface is None:
            if bus_type == "system":
                bus = self.system
            else:
                bus = self.session
            iface = await get_interface(bus, service, path, interface)
            self.interfaces[name] = iface

        return iface

    async def register_signal(self, signal_alias: str, callback: Callable) -> None:
        """Register a signal handler"""
        iface_name, signal_name = SIGNALS[signal_alias]["interface"], SIGNALS[signal_alias]["name"]
        iface = await self.get_interface(iface_name)
        getattr(iface, signal_name)(callback)
        logger.info("Registered signal callback for interface:%s, signal:%s", iface_name, signal_name)
        SIGNALS["subscribed"].append((signal_alias, callback))
