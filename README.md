# Home Assistant Linux Companion

Application to run on Linux desktop computer to provide sensor data to Home Assistant, and get notifications as if it was a mobile device.

## How To

### Requirements

Python 3.10+ and the related `dev` dependencies (usually `python3-dev` or `python3-devel` on your package manager)

### Instructions

1. [Get a long-lived access token from your Home Assistant user](https://www.atomicha.com/home-assistant-how-to-generate-long-lived-access-token-part-1/)
1. Clone this repository.
1. Create a Python virtual environment and install all the requirements:

   ```shell
   cd halinuxcompanion
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

1. Copy `config.example.json` to `config.json`.
1. Modify `config.json` to match your setup and desired options.
1. Run the application from the virtual environment: `python -m halinuxcompanion --config config.json`
    - Alternatively set up a systemd service using the [provided unit file](halinuxcompanion/resources/halinuxcompanion.service)

Now in your Home Assistant you will see a new device in the **"mobile_app"** integration, and there will be a new service to notify your Linux desktop. Notification actions work and the expected events will be fired in Home Assistant.

## [Example configuration file](config.example.json)

```json
{
  "ha_url": "http://homeassistant.local:8123/",
  "ha_token": "mysuperlongtoken",
  "device_id": "computername",
  "device_name": "whatever you want can be left empty",
  "manufacturer": "whatever you want can be left empty",
  "model": "Computer",
  "computer_ip": "192.168.1.15",
  "computer_port": 8400,
  "refresh_interval": 15,
  "loglevel": "INFO",
  "sensors": {
    "cpu": {
      "enabled": true,
      "name": "CPU"
    },
    "memory": {
      "enabled": true,
      "name": "Memory Load"
    },
    "uptime": {
      "enabled": true,
      "name": "Uptime"
    },
    "status": {
      "enabled": true,
      "name": "Status"
    },
    "battery_level": {
      "enabled": true,
      "name": "Battery Level"
    },
    "battery_state": {
      "enabled": true,
      "name": "Battery State"
    },
    "camera_state": {
      "enabled": true,
      "name": "Camera State"
    }
  },
  "services": {
    "notifications": {
      "enabled": true,
      "url_program": "xdg-open",
      "commands": {
        "command_suspend": {
          "name": "Suspend",
          "command": ["systemctl", "suspend"]
        },
        "command_poweroff": {
          "name": "Power off",
          "command": ["systemctl", "poweroff"]
        },
        "command_reboot": {
          "name": "Reboot",
          "command": ["systemctl", "reboot"]
        },
        "command_hibernate": {
          "name": "Hibernate",
          "command": ["systemctl", "hibernate"]
        },
        "command_open_ha": {
          "name": "Open Home Assistant",
          "command": ["xdg-open", "http://homeassistant.local:8123/"]
        },
        "command_open_spotify": {
          "name": "Open Spotify Flatpak",
          "command": ["flatpak", "run", "com.spotify.Client"]
        }
      }
    }
  }
}
```

## Technical

- [Home Assistant Native App Integration](https://developers.home-assistant.io/docs/api/native-app-integration)
- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest)
- Asynchronous (because why not :smile:)
  - HTTP Server ([aiohttp](https://docs.aiohttp.org/en/stable/)): Listen to POST notification service call from Home Assistant
  - Client ([aiohttp](https://docs.aiohttp.org/en/stable/)): POST to Home Assistant api, sensors, events, etc
  - [Dbus](https://www.freedesktop.org/wiki/Software/dbus/) interface ([dbus_next](https://python-dbus-next.readthedocs.io/en/latest/index.html)): Sending notifications and listening to notification actions from the desktop, also listens to sleep, shutdown to update the status sensor

## To-do

- [ ] [Implement encryption](https://developers.home-assistant.io/docs/api/native-app-integration/sending-data)
- [ ] Move sensors to MQTT  
    The reasoning for the change is the limitations of the API, naturally is expected that desktop and laptops would go offline and I would like for the sensors to reflect this new state. But if for some reason the application is unable to send this new state to Home Assistant the values of the sensors would be stuck. But if the app uses MQTT it can set will topics for the sensors to be updated when the client can't communicate with the server.
- [ ] One day make it work with remote and local instance, for laptops roaming networks
- [x] Status sensors that listens to sleep, wakeup, shutdown, power_on
- [ ] Add more sensors
- [ ] Finish notifications functionality
    - [x] Add notification commands
    - [x] [Notifications Clearing](https://companion.home-assistant.io/docs/notifications/notifications-basic/#clearing)
    - [ ] [Notification Icon](https://companion.home-assistant.io/docs/notifications/notifications-basic/#notification-icon)

## Features

- Sensors:
  - CPU
  - Memory
  - Uptime
  - Status: Computer status, reflects if the computer went to sleep, wakes up, shutdown, turned on. The sensor is updated right before any of these events happen by listening to dbus signals.
  - Battery Level
  - Batter State
- Notifications:
  - [Actionable Notifications](https://companion.home-assistant.io/docs/notifications/actionable-notifications#building-actionable-notifications) (Triggers event in Home Assistant)
      - [Local action handler using URI](https://companion.home-assistant.io/docs/notifications/actionable-notifications#uri-values): only relative style `/lovelace/myviwew` and `http(s)` uri supported so far.
  - [Notification cleared/dismissed](https://companion.home-assistant.io/docs/notifications/notification-cleared/) (Triggers event in Home Assistant)
  - [Timeout](https://companion.home-assistant.io/docs/notifications/notifications-basic#notification-timeout)
  - [Commands](https://companion.home-assistant.io/docs/notifications/notification-commands/)
  - [Replacing](https://companion.home-assistant.io/docs/notifications/notifications-basic/#replacing)
  - [Clearing](https://companion.home-assistant.io/docs/notifications/notifications-basic/#clearing)
  - [Icon](https://companion.home-assistant.io/docs/notifications/notifications-basic/#notification-icon) **TODO**
- Default commands (example config):
  - Suspend
  - Power off
  - Reboot
  - Hibernate
