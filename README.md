# Home Assistant Linux Companion

Application to run on linux desktop computer to provide sensors data to homeasssistant, and get notifications as if it was a mobile device.

## How To

1. [Get a long lived access token from your homeasssistant user](https://www.atomicha.com/home-assistant-how-to-generate-long-lived-access-token-part-1/)
1. Install requirements `pip3 install -r requirements.txt`
1. Modify `config.json` to match your setup and desired options.
1. Run the application `python3 -m halinuxcompanion --config config.json`
    - Alternative setup a systemd service using the [provided unit file](halinuxcompanion/resources/halinuxcompanion.service)

Now in your homeasssistant you will see a new device in th-**"mobile_app"** integration, and there will be a new service to notify your linux desktop. Notification actions work and the expected events will be fired in Home Assistant.

## [Example configuration file](/config.json)

```json
{
  "ha_url": "http://localhost:8123",
  "ha_token": "mysuperlongtoken",
  "device_id": "computername",
  "device_name": "whatever you want can be left empty",
  "manufacturer": "whatever you want can be left empty",
  "model": "Computer",
  "computer_ip": "192.168.1.15",
  "computer_port": 8400,
  "refresh_interval": "15",
  "loglevel": "INFO",
  "sensors": {
    "cpu": {
      "enabled": true,
      "name": "CPU",
      "icon": "mdi:cpu-64-bit"
    },
    "memory": {
      "enabled": true,
      "name": "Memory Load",
      "icon": "mdi:memory"
    },
    "uptime": {
      "enabled": true,
      "name": "Uptime",
      "icon": "mdi:memory"
    },
    "status": {
      "enabled": true,
      "name": "Status",
      "icon": "mdi:desktop-classic"
    }
  },
  "services": {
    "notifications": {
      "enabled": true
    },
    "url_handler": {
      "enabled": true,
      "program": "xdg-open"
    }
  }
}
```

## Technical

- [Home Assistant Native App Integration](https://developers.home-assistant.io/docs/api/native-app-integration)
- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest)
- Asynchronous (because why not :smile:)
  - HTTP Server (aiohttp): Listen to POST notification service call from Home Assistant
  - Client (aiohttp): POST to Home Assistant api, sensors, events, etc
  - Dbus interface (dbus_next): Sending notifications and listening to notification actions from the desktop, also listens to sleep, shutdown to update the state sensor

## Todo

- [ ] [Implement encryption](https://developers.home-assistant.io/docs/api/native-app-integration/sending-data)
- [ ] Move sensors to MQTT  
    The reasoning for the change is the limitations of the API, naturally is expected that desktop and laptops would go offline and I would like for the sensors to reflect this new state. But if for some reason the application is unable to send this new state to Home Assistant the values of the sensors would be stuck. But if the app uses MQTT it can set will topics for the sensors to be updated when the client can't communicate with the server.
- [ ] Finish notifications funtionality
- [ ] One day make it work with remote and local instance, for laptops roaming networks
- [x] Status sensors that listens to sleep, wakeup, shutdown, power_on~~
- [ ] Add more sensors

## Features

- Sensors:
  - CPU
  - Memory
  - Uptime
  - Status: Computer status, reflects if the computer went to sleep, wakes up, shutdown, turned on. The sensor is updated right before any of this events happens by listening for dbus signals.
- Notifications:
  - Actions Callback (Triggers event in Home Assistant)
  - Actions Locally (If action contains)
  - Closing/Removing/Dismissing Callback (Triggers event in Home Assistant)
  - Timeout
  - Commands **TODO**
  - Replacing, dismissing from Home Assistant **TODO**
  - Icon (Currently the Home Assistant icon is hard coded) **TODO**
