from dbus_next.aio import MessageBus, ProxyInterface
from dbus_next import BusType
from typing import Callable
import logging

logger = logging.getLogger(__name__)

SIGNALS = {
    "session.notification_on_action_invoked": {
        "type": "session",
        "name": "on_action_invoked",
        "interface": "org.freedesktop.Notifications",
    },
    "session.notification_on_notification_closed": {
        "type": "session",
        "name": "on_notification_closed",
        "interface": "org.freedesktop.Notifications",
    },
    "system.login_on_prepare_for_sleep": {
        "type": "system",
        "name": "on_prepare_for_sleep",
        "interface": "org.freedesktop.login1.Manager",
    },
    "system.login_on_prepare_for_shutdown": {
        "type": "system",
        "name": "on_prepare_for_shutdown",
        "interface": "org.freedesktop.login1.Manager",
    },
    "subscribed": [],
}

INTERFACES = {
    "org.freedesktop.login1.Manager": {
        "type": "system",
        "interface": "org.freedesktop.login1",
        "path": "/org/freedesktop/login1",
        "proxy_interface": "org.freedesktop.login1.Manager"
    },
    "org.freedesktop.Notifications": {
        "type": "session",
        "interface": "org.freedesktop.Notifications",
        "path": "/org/freedesktop/Notifications",
        "proxy_interface": "org.freedesktop.Notifications"
    },
}


async def get_interface(bus, interface, path, proxy_interface):
    introspection = await bus.introspect(interface, path)
    proxy = bus.get_proxy_object(interface, path, introspection)
    return proxy.get_interface(proxy_interface)


class Dbus:
    session: MessageBus
    system: MessageBus
    interfaces: dict[str, ProxyInterface] = {}

    async def init(self) -> None:
        self.system = await MessageBus(bus_type=BusType.SYSTEM).connect()
        self.session = await MessageBus(bus_type=BusType.SESSION).connect()

    async def get_interface(self, name: str) -> ProxyInterface:
        i = INTERFACES[name]
        type, interface, path, proxy_interface = i["type"], i["interface"], i["path"], i["proxy_interface"]
        iface = self.interfaces.get(name)
        if iface is None:
            if type == "system":
                bus = self.system
            else:
                bus = self.session
            iface = await get_interface(bus, interface, path, proxy_interface)
            self.interfaces[name] = iface

        return iface

    async def register_signal(self, signal_alias: str, callback: Callable) -> None:
        """Register a signal handler"""
        iface_name, signal_name = SIGNALS[signal_alias]["interface"], SIGNALS[signal_alias]["name"]
        iface = await self.get_interface(iface_name)
        getattr(iface, signal_name)(callback)
        logger.info("Registered signal callback for interface:%s, signal:%s", iface_name, signal_name)
        SIGNALS["subscribed"].append((signal_alias, callback))
