from halinuxcompanion.api import API

import asyncio
from aiohttp.web import Response
from dbus_next.aio import ProxyInterface
from dbus_next.signature import Variant
from importlib.resources import path as resource_path
from typing import Dict, List
import json
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
    history: Dict[int, dict] = {}  # Keeps a history of notifications
    tagtoid: Dict[int, str] = {}  # Lookup id from tag
    interface: ProxyInterface
    api: API
    device_id: str

    def __init__(self):
        pass

    async def init(self, bus, api, webserverver, device_id):
        """Function to initialize the notifier.
        1. Handles creating the ProxyInterface to send notifications and listen to events.
        2. Registers an http handler to the webserver for Home Assistant notifications.
        3. Register callbacks for dbus events (on_action_invoked and on_notification_closed).
        4. Keeps a reference to the API for firing events in Home Assistant.
        5. Sets the device id for notification calls.
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
        # API and Companion reference
        self.api = api
        self.device_id = device_id

    async def dbus_notify(self, notification: dict):
        """Function to send a native dbus notification.
        According to the following link:
            Section  org.freedesktop.Notifications.Notify
            https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#protocol
        """
        id = await self.interface.call_notify(APP_NAME, notification["replace_id"], notification["icon"],
                                              notification["title"], notification["message"], notification["actions"],
                                              notification["hints"], notification["timeout"])

        # Store in the history
        self.history[id] = notification
        tag = notification["data"].get("tag", None)
        if tag:
            self.tagtoid[tag] = id

        logger.info("Dbus notification dispatched id:%s", id)

    async def on_ha_notification(self, request) -> Response:
        """Function that handles the notification POST request by Home Assistant.
        This function is called by the http server when a notification is received, it converts the
        notification to the format dbus uses and emits it.
        """
        hanot: dict = await request.json()
        if "data" not in hanot:
            hanot["data"] = {}
        logging.info("Received notification request:%s", hanot)  # TODO: Move to debug once 1.0
        asyncio.create_task(self.dbus_notify(self.ha_notification_to_dbus(hanot)))
        return Response(text="OK")

    async def on_action(self, id, action):
        """Function to handle the dbus notification action event"""
        notification = self.history.get(id, None)
        logger.info("Notification action received: id:%s, action:%s", id, action)
        # Default action is not sent, since is just clicking the notification
        # Also don't send if the data can't be found
        # TODO: REFACTOR THIS LOGIC, IS BEING REPEATED IN on_close TODO
        if notification and action != "default":
            data = self.event_data(id=id, action=action)
            asyncio.create_task(self.api.post("/api/events/mobile_app_notification_action", json.dumps(data)))

    async def on_close(self, id, reason):
        """Function to handle the dbus notification close event"""
        hanot = self.history.get(id, {})
        tag = hanot.get("data", {}).get("tag", "NOTAG")
        logger.info("Notification closed received: id:%s, tag:%s reason:%s", id, tag, reason)
        if hanot:
            data = self.event_data(id)
            asyncio.create_task(self.api.post("/api/events/mobile_app_notification_cleared", json.dumps(data)))

    def event_data(self, id: int, action: str = "") -> dict:
        """Function to get the event data given an event type and notification id"""
        notification = self.history.get(id, None)
        data = {}
        if notification:
            data = {
                "title": notification.get("title", ""),
                "message": notification.get("message", ""),
                **notification.get("event_actions", {}),
                **notification["data"],
            }
            data.pop("actions")  # Replaced by event_actions
            if action != "":
                data["action"] = action

        return data

    def ha_notification_to_dbus(self, hanot: dict) -> dict:
        """Function to convert a homeassistant notification to a dbus notification.
        This is done in a best effort manner, as the homeassistant notification format can't be fully translated.
        """
        data: dict = hanot["data"]
        actions: List[str] = []
        hints: Dict[str, Variant] = {}
        icon: str = HA_ICON  # Icon path
        timeout: int = -1  # -1 means notification server decides how long to show
        if data:
            # Actions: Actions

            # https://companion.home-assistant.io/docs/notifications/actionable-notifications
            # https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#basic-design

            # Actions are as such [id, name, id, name, ...]
            event_actions = {}  # Format the actions as neccessary for on_close an on_action events
            counter = 1
            if "url" in data:
                actions.extend(["default", "Default Action"])
            elif "clickAction" in data:
                actions.extend(["default", data["Default Action"]])
            for a in data.get("actions", []):
                actions.extend([a["action"], a["title"]])
                # This is necessary when sending event data on_closed, on_action
                event_actions[f"action_{counter}_key"] = a["action"]
                event_actions[f"action_{counter}_title"] = a["title"]

            hanot["event_actions"] = event_actions

            # Hints: Importance: Urgency

            # https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#urgency-levels
            # https://companion.home-assistant.io/docs/notifications/notifications-basic/#notification-channel-importance
            urgency = URGENCY_NORMAL  # Normal level
            if "importance" in data:
                urgency = NOTIFY_LEVELS.get(data["importance"], URGENCY_NORMAL)
            hints["urgency"] = urgency

            # Timeout
            timeout = data.get("duration", timeout)

        hanot.update({
            "title": hanot.get("title", ""),
            "actions": actions,
            "hints": hints,
            "timeout": timeout,
            "icon": icon,  # TODO: Support custom icons
            "replace_id": 0,  # TODO: Implement
        })
        logger.debug("Converted notification: %s", hanot)

        return hanot
