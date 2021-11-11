# Home Assistant Linux Companion

Application to run on linux desktop computer to provide sensors data to homeasssistant, and get notifications as if it was a mobile device.

## How To

1. [Get a long lived access token from your homeasssistant user](https://www.atomicha.com/home-assistant-how-to-generate-long-lived-access-token-part-1/)
1. Install requirements `pip3 install -r requirements.txt`
1. Fill `config.json`, the example data is provided in `config-sample.json`.
1. Run the application `python3 -m halinuxcompanion --config config.json`

## Example configuration file

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
      "name": "CPU",
      "icon": "mdi:memory"
    }
  },
  "services": {
    "notifications": {
      "enabled": true
    }
  }
}
```

## Technical

- Uses only the [Native App Integration](https://developers.home-assistant.io/docs/api/native-app-integration)
- Asynchronous (because why not :smile:)

## Todo

- [**Implement encryption**](https://developers.home-assistant.io/docs/api/native-app-integration/sending-data)
- [**Native notifications**](https://developers.home-assistant.io/docs/api/native-app-integration/notifications)
- **Move sensors to MQTT**  
  The reasoning for the change is the limitations of the API, naturally is expected that desktop and laptops would go offline and I would like for the sensors to reflect this new state. But if for some reason the application is unable to send this new state to Home Assistant the values of the sensors would be stuck. But if the app uses MQTT it can set will topics for the sensors to be updated when the client can't communicate with the server.
