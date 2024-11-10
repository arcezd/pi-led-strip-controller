# Led Strip

Project DYI for a NeoPixel led strip controlled by a Raspverry Pi and integrated to Homebridge using [mqtthings](https://github.com/arachnetech/homebridge-mqttthing).

## Variables

| Variable | Description | Default value |
|----------|-------------|---------------|
| DEVICE_ID | Device name for the mqtt topics | rpi4_debug |
| LEDS_NUM | Led strip number of leds |
| PIXELS_ORDER | Pixels order for the led strip (RGB, GRB, BRG) | RGB |
| MQTT_HOST | MQTT server hostname |
| MQTT_PORT | MQTT server port |
| MQTT_USERNAME | MQTT server username |
| MQTT_CA_CERT_PATH | MQTT TLS CA certificate path | 
| MAX_RETRIES | Max retries to connect to MQTT server | 10 |
| BACKOFF_FACTOR | Backoff factor to be used for retries to connect to mqtt | 2 |

## Getting started
Install the python dependencies using the command:
```bash
/usr/bin/python3 -m pip install -r requirements.txt
```

Modify the environment variables file setting the required values
```bash
cp .env.example .env
vi .env
```

Execute the program using sudo (required by neopixel)
```bash
export $(cat .env | xargs)

sudo --preserve-env=MQTT_HOST \
  --preserve-env=MQTT_PORT \
  --preserve-env=MQTT_USERNAME \
  --preserve-env=MQTT_USERNAME \
  --preserve-env=MQTT_PASSWORD \
  python3 mqtt-control.py > led-rainbown.log &
```

## Homebridge setup

Add the following configuration to the homebridge config.json file, replacing the DEVICE_ID, MQTT_HOST, MQTT_PORT, MQTT_USERNAME and MQTT_CA_CERT_PATH values as required.
```json
{
  "type": "lightbulb",
  "name": "DeskLED",
  "url": "mqtts://mqtt-server:8884",
  "username": "homebridge",
  "password": "super_secret_password",
  "mqttOptions": {
      "cafile": "/homebridge/certs/mqtt-ca.crt"
  },
  "logMqtt": true,
  "topics": {
      "getOnline": "stat/[DEVICE_ID]/STATUS",
      "setOn": "cmnd/[DEVICE_ID]/POWER",
      "getOn": "stat/[DEVICE_ID]/POWER",
      "getHSV": "stat/[DEVICE_ID]/HSBColor",
      "setHSV": "cmnd/[DEVICE_ID]/HSBColor"
  },
  "onlineValue": "Online",
  "offlineValue": "Offline",
  "onValue": "ON",
  "offValue": "OFF",
  "accessory": "mqttthing"
},
{
  "type": "lightbulb",
  "name": "DeskLED Rainbow",
  "url": "mqtts://mqtt-server:8884",
  "username": "homebridge",
  "password": "super_secret_password",
  "mqttOptions": {
      "cafile": "/homebridge/certs/mqtt-ca.crt"
  },
  "logMqtt": true,
  "topics": {
      "getOnline": "stat/[DEVICE_ID]/STATUS",
      "setOn": "cmnd/[DEVICE_ID]/effects/rainbow/set",
      "getOn": "stat/[DEVICE_ID]/effects/rainbow"
  },
  "onlineValue": "Online",
  "offlineValue": "Offline",
  "onValue": "ON",
  "offValue": "OFF",
  "accessory": "mqttthing"
}
```

## 