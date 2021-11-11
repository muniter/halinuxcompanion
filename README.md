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


