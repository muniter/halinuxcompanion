import asyncio
from aiohttp.web import Response
from dbus_next.aio import ProxyInterface
from dbus_next.signature import Variant
from importlib.resources import path as resource_path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

APP_NAME = "halinuxcompanion"
with resource_path(f"{APP_NAME}.resources", "home-assistant-favicon.png") as p:
    HA_ICON = str(p.absolute())

# Urgency levels
# https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#urgency-levels
URGENCY_LOW = Variant("u", 0)
URGENCY_NORMAL = Variant("u", 1)
URGENCY_CRITICAL = Variant("u", 2)
NOTIFY_LEVELS = {
    "min": URGENCY_LOW,
    "low": URGENCY_LOW,
    "default": URGENCY_NORMAL,
    "high": URGENCY_CRITICAL,
    "max": URGENCY_CRITICAL,
}


class Notifier:
    """Class to handle notifications"""
    notifications: dict  # TODO: Implement
    interface: ProxyInterface

    def __init__(self):
        pass

    async def init(self, bus, webserverver):
        """Function to initialize the notifier.
        1. Handles creating the ProxyInterface to send notifications and listen to events.
        2. Registers an http handler to the webserver for Home Assistant notifications.
        3. Register callbacks for dbus events (on_action_invoked and on_notification_closed).
        """
        interface = 'org.freedesktop.Notifications'
        path = '/org/freedesktop/Notifications'
        introspection = await bus.introspect(interface, path)
        proxy = bus.get_proxy_object(interface, path, introspection)
        self.interface = proxy.get_interface(interface)
        # Setup dbus callbacks
        self.interface.on_action_invoked(self.on_action)
        self.interface.on_notification_closed(self.on_close)
        # Setup http server route handler for incoming notifications
        webserverver.app.router.add_route('POST', '/notify', self.on_ha_notification)

    async def dbus_notify(self, title="", message="", icon=HA_ICON, actions=[], hints={}, timeout=-1, replace_id=0):
        """Function to send a native dbus notification.
        According to the following link:
            Section  org.freedesktop.Notifications.Notify
            https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#protocol
        """
        id = await self.interface.call_notify(APP_NAME, replace_id, icon, title, message, actions, hints, timeout)
        print("Got id back", id)

    async def on_ha_notification(self, request) -> Response:
        """Function that handles the notification POST request by Home Assistant.
        This function is called by the http server when a notification is received, it converts the
        notification to the format dbus uses and emits it.
        """
        data: dict = await request.json()
        logging.info("Received notification request:%s", data)  # TODO: Move to debug once 1.0
        asyncio.create_task(self.dbus_notify(**self.ha_notification_to_dbus(data)))
        return Response(text="OK")

    async def on_action(self, id, reason):
        """Function to handle the dbus notification action event"""
        logger.info("Notification action id:%s, reason:%s", id, reason)

    async def on_close(self, id, action):
        """Function to handle the dbus notification close event"""
        logger.info("Notification closed: id:%s, reason:%s", id, action)

    def ha_notification_to_dbus(self, notification: dict) -> dict:
        """Function to convert a homeassistant notification to a dbus notification.
        This is done in a best effort manner, as the homeassistant notification format can't be fully translated.
        """
        data: dict = notification.get("data", {})
        actions: List[str] = []
        hints: Dict[str, Variant] = {}
        icon: str = HA_ICON  # Icon path
        timeout: int = -1  # -1 means notification server decides how long to show
        if data:
            # Actions: Actions

            # https://companion.home-assistant.io/docs/notifications/actionable-notifications
            # https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#basic-design

            # Actions are as such [id, name, id, name, ...]
            if "url" in data:
                actions.extend(["default", "Default Action"])
            elif "clickAction" in data:
                actions.extend(["default", data["Default Action"]])
            for a in data.get("actions", []):
                actions.extend([a["action"], a["title"]])

            # Hints: Importance: Urgency

            # https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#urgency-levels
            # https://companion.home-assistant.io/docs/notifications/notifications-basic/#notification-channel-importance
            urgency = URGENCY_NORMAL  # Normal level
            if "importance" in data:
                urgency = NOTIFY_LEVELS.get(data["importance"], URGENCY_NORMAL)
            hints["urgency"] = urgency

            # Timeout
            timeout = data.get("duration", timeout)

        notification = {
            "title": notification.get("title", ""),
            "message": notification.get("message", ""),
            "actions": actions,
            "hints": hints,
            "timeout": timeout,
            "icon": icon,  # TODO: Support custom icons
            # "replace_id": "",  # TODO: Implement
        }
        logger.info("Converted notification: %s", notification)

        return notification
