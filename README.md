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

## 