from halinuxcompanion.companion import CommandConfig, Companion
from halinuxcompanion.api import API, Server
from halinuxcompanion.dbus import Dbus

import asyncio
from aiohttp.web import Response, json_response
from aiohttp import ClientError
from dbus_next.aio import ProxyInterface
from dbus_next.signature import Variant
from importlib.resources import path as resource_path
from collections import OrderedDict
from typing import Dict, List
import json
import re
import logging

logger = logging.getLogger(__name__)

APP_NAME = "halinuxcompanion"
HA = "Home Assistant"
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

EVENTS_ENPOINT = {
    "closed": "/api/events/mobile_app_notification_cleared",
    "action": "/api/events/mobile_app_notification_action",
}

RESPONSES = {
    "invalid_token": json.dumps(
        {
            "error": "push_token does not match",
            "errorMessage": "Sent token that does not match to halinuxcompaion munrig",
        }
    ).encode("ascii"),
    "ok": json.dumps({"success": True, "message": "Notification queued"}).encode(
        "ascii"
    ),
}

EMPTY_DICT = {}


class Notifier:
    """Class that handles the lifetime of notifications
    1. It receives a notification by registering a handler to the web server spawned by the application.
    2. It transforms the notification to the format dbus uses.
    3. It sets up the proxy object to send dbus notifications, and listen to events related to this notifications.
    4. It sends the notification to dbus.
    5. Listens to the dbus events related to this notification.
    6. When dbus events are generated, it emits the event to Home Assistant (if appropieate).
    7. Some action events perform a local action like opening a url.
    """

    # Only keeping the last 20 notifications and popping everytime a new one is added
    history: OrderedDict[int, dict] = OrderedDict(
        (x, EMPTY_DICT) for x in range(-1, -21, -1)
    )
    tagtoid: Dict[str, int] = {}  # Lookup id from tag
    interface: ProxyInterface
    api: API
    push_token: str
    url_program: str
    commands: Dict[str, CommandConfig]
    ha_url: str

    def __init__(self):
        # The initialization is done in the init function
        pass

    async def init(
        self, dbus: Dbus, api: API, webserverver: Server, companion: Companion
    ) -> None:
        """Function to initialize the notifier.
        1. Gets the dbus interface to send notifications and listen to events.
        2. Registers an http handler to the webserver for Home Assistant notifications.
        3. Register callbacks for dbus events (on_action_invoked and on_notification_closed).
        4. Keeps a reference to the API for firing events in Home Assistant.
        5. Sets the push_token used to check if the notification is for this device.
        6. Sets the url_program used to open urls.

        :param dbus: The Dbus class abstraction
        """
        # Get the interface
        interface = await dbus.get_interface("org.freedesktop.Notifications")

        if interface is None:
            logger.warning(
                "Could not find org.freedesktop.Notifications interface, disabling notification support."
            )
            return

        self.interface = interface
        # Setup dbus callbacks
        self.interface.on_action_invoked(self.on_action)
        self.interface.on_notification_closed(self.on_close)

        # Setup http server route handler for incoming notifications
        webserverver.app.router.add_route("POST", "/notify", self.on_ha_notification)

        # API and necessary data
        self.api = api
        self.push_token = companion.app_data["push_token"]
        self.url_program = companion.url_program
        self.commands = companion.commands
        self.ha_url = companion.ha_url

    # Entrypoint to the Class logic
    async def on_ha_notification(self, request) -> Response:
        """Function that handles the notification POST request by Home Assistant.

        This is the only entry point to start logic in this class.
            This function is called by the http server when a notification is received. The notification is transformed
            to the format dbus uses, and sent to dbus.

        :param request: The request object
        :return: The response object
        """
        notification: dict = await request.json()
        push_token = notification.get("push_token")
        logger.info("Received notification request:%s", notification)

        # Check if the notification is for this device
        if push_token != self.push_token:
            logger.error(
                "Notification push_token does not match: %s != %s",
                push_token,
                self.push_token,
            )
            return json_response(body=RESPONSES["invalid_token"], status=400)

        # Transform the notification to the format dbus uses
        notification = self.notification_transform(notification)

        if notification["is_command"]:
            command_id = notification["message"]
            command = self.commands.get(command_id)
            if command:
                # It's not a notification, but a command, therefore no dbus_notify
                logger.info(
                    "Received notification command: id:%s name:%s", command_id, command.name
                )
                logger.info("Scheduling notification command: %s", command.command)
                asyncio.create_task(
                    asyncio.create_subprocess_exec(
                        *command.command,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                )
            else:
                # Got notificatoin command but none defined
                logger.error(
                    "Received notification command %s, but no command is defined",
                    command_id,
                )
        else:
            asyncio.create_task(
                self.dbus_notify(self.notification_transform(notification))
            )

        return json_response(body=RESPONSES["ok"], status=201)

    async def ha_event_trigger(
        self, event: str, action: str = "", notification: dict = {}
    ) -> bool:
        """Function to trigger the Home Assistant event given an event type and notification dictionary.
        Actions are first handled in on_action which decides wether to emit the event or not.

        :param event: The event type
        :param action: The action that was invoked (if any)
        :param notification: The notification dictionary
        :return: True if the event was triggered, False otherwise
        """
        endpoint = EVENTS_ENPOINT[event]

        if notification:
            data = {
                "title": notification.get("title", ""),
                "message": notification.get("message", ""),
                **notification.get("event_actions", {}),
                **notification["data"],
            }
            # Replaced by event_actions
            if "actions" in data:
                del data["actions"]

            if event == "action":
                data["action"] = action

            try:
                res = await self.api.post(endpoint, json.dumps(data))
                logger.info(
                    "Sent Home Assistant event:%s data:%s response:%s",
                    endpoint,
                    data,
                    res.status,
                )
                return True
            except ClientError as e:
                logger.error("Error sending Home Assistant event: %s", e)

        return False

    def notification_transform(self, notification: dict) -> dict:
        """Function to convert a Home Assistant notification to a dbus notification.
        This is done in a best effort manner, as the homeassistant notification format can't be fully translated.
        This function mutates the notification dict.

        :param notification: The notification to convert (mutated)
        :return: The mutated notification passed with the necessary fields to invoke a dbus notification.
        """
        # Add the data, avoids the need to check (branching) ahead
        data: dict = notification.setdefault("data", {})
        tag: str = data.setdefault("tag", "")
        actions: List[str] = ["default", "Default"]
        hints: Dict[str, Variant] = {}
        icon: str = HA_ICON  # Icon path
        timeout: int = -1  # -1 means notification server decides how long to show
        replace_id: int = 0
        if notification["message"].startswith("command_"):
            # This is a command notification, short circuit the rest of the logic, no need to format the notification
            # since it won't be stored nor emitted by dbus.
            notification["is_command"] = True
            return notification

        elif data:
            # Actions
            # Home Assisnant actions require seome transformation
            # https://companion.home-assistant.io/docs/notifications/actionable-notifications
            # https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#basic-design

            # Dbus notification structure [id, name, id, name, ...]
            event_actions = (
                {}
            )  # Format the actions as necessary for on_close an on_action events
            counter = 1
            for a in data.get("actions", []):
                actions.extend([a["action"], a["title"]])
                # This is necessary when sending event data on_closed, on_action
                event_actions[f"action_{counter}_key"] = a["action"]
                event_actions[f"action_{counter}_title"] = a["title"]

            notification["event_actions"] = event_actions
            # Uri for the default action
            uri = data.get("url", "") or data.get("clickAction", "")
            # check if uri starts with /lovelace or lovelace using regex
            if uri and re.match(r"^/?lovelace", uri):
                uri = f'{self.ha_url}/{uri.lstrip("/")}'
            notification["default_action_uri"] = uri

            # Hints:
            # Importance -> Urgency
            # https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#urgency-levels
            # https://companion.home-assistant.io/docs/notifications/notifications-basic/#notification-channel-importance
            urgency = URGENCY_NORMAL  # Normal level
            if "importance" in data:
                urgency = NOTIFY_LEVELS.get(data["importance"], URGENCY_NORMAL)
            hints["urgency"] = urgency

            # Timeout, convert milliseconds to seconds
            if "timeout" in data:
                try:
                    timeout = int(data["timeout"]) * 1000
                except ValueError:
                    pass

            # Replaces id:
            # Using the notification tag, check if it should replace an existing notification
            replace_id = self.tagtoid.get(tag, 0)

            # Dismiss/clear notification
            if notification["message"] == "clear_notification":
                logger.info("Clearing notification: %s", notification)
                # Replace the notification and hide it in 1 millisecond, workaround for dbus notifications
                timeout = 1

        notification.update(
            {
                "title": notification.get("title", HA),
                "actions": actions,
                "hints": hints,
                "timeout": timeout,
                "icon": icon,  # TODO: Support custom icons
                "replace_id": replace_id,
                "is_command": False,
            }
        )
        logger.debug("Converted notification: %s", notification)

        return notification

    async def dbus_notify(self, notification: dict) -> None:
        """Function to send a native dbus notification.
        According to the following link:
            Section  org.freedesktop.Notifications.Notify
            https://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html#protocol

        :param notification: The notification to send, at this point it should be transformed to the format dbus uses,
            from the format Home Assistant sends.
        :return: None
        """
        logger.info("Sending dbus notification")
        id = await self.interface.call_notify(
            APP_NAME,
            notification["replace_id"],
            notification["icon"],
            notification["title"],
            notification["message"],
            notification["actions"],
            notification["hints"],
            notification["timeout"],
        )
        logger.info("Dbus notification dispatched id:%s", id)

        # History management: Add the new notification, and remove the oldest one.
        # Storage
        self.history[id] = notification
        tag: str = notification["data"].get("tag", None)
        if tag:
            self.tagtoid[tag] = id

        # Removal
        _, old_not = self.history.popitem(last=False)
        otag = old_not.get("data", {}).get("tag", "")
        if otag in self.tagtoid:
            self.tagtoid.pop(otag)

    async def on_action(self, id: int, action: str) -> None:
        """Function to handle the dbus notification action event
        If a notifications is found, and the action is not the default action, an event is triggered to home assistant.
        (This is how the android app handles actions).

        :param id: The dbus id of the notification
        :param action: The action that was invoked
        """
        logger.info(
            "Notification action dbus event received: id:%s, action:%s", id, action
        )
        notification: dict = self.history.get(id, {})
        if not notification:
            logger.info(
                "No notification found for id:%s, doesn't belong to this applicaton", id
            )
            return

        actions: List[dict] = notification["data"].get("actions", {})
        if actions or action == "default":
            uri: str
            emit_event: bool = True
            # actions is a list of dictionaries {"action": "turn_off", "title": "Turn off House", "uri": "http://..."}
            if action == "default":
                uri = notification.get("default_action_uri", "")
                emit_event = False
            else:
                uri = next(filter(lambda dic: dic["action"] == action, actions)).get(
                    "uri", ""
                )

            if uri.startswith("http") and self.url_program != "":
                asyncio.create_task(
                    asyncio.create_subprocess_exec(self.url_program, uri)
                )
                logger.info("Launched action:%s uri:%s", action, uri)

            if emit_event:
                asyncio.create_task(
                    self.ha_event_trigger("action", action, notification)
                )

    async def on_close(self, id: int, reason: str) -> None:
        """Function to handle the dbus notification close event
        Sends the data to ha_event_trigger, where the event is created and sent to Home Assistant.

        :param id: The dbus id of the notification
        :param reason: The reason the notification was closed
        """
        logger.info(
            "Notification closed dbus event received: id:%s, reason:%s", id, reason
        )
        notification = self.history.get(id, {})
        if notification:
            asyncio.create_task(
                self.ha_event_trigger(event="closed", notification=notification)
            )
        else:
            logger.info(
                "No notification found for id:%s, doesn't belong to this applicaton", id
            )
