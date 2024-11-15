# rpi - led strip controller
import os
import sys
import time
import board
import colorsys
import neopixel
import paho.mqtt.client as mqtt
import logging
from logging.handlers import SysLogHandler
from signal import SIGKILL, SIGTERM, signal

def setup_logger(logger):
    logger.setLevel(logging.INFO)

    # SysLogHandler for journald
    syslog_handler = SysLogHandler(address='/dev/log')  # Unix socket for Syslog
    formatter = logging.Formatter('%(name)s: %(levelname)s %(message)s')
    syslog_handler.setFormatter(formatter)
    logger.addHandler(syslog_handler)


# configure logging to send messages to Syslog
logger = logging.getLogger("led-strip")
setup_logger(logger)


## MQTT Settings
DEVICE_ID = os.environ.get("DEVICE_ID", "rpi4_debug")
LEDS_NUM = os.environ.get("LEDS_NUM")
PIXELS_ORDER = os.environ.get("PIXELS_ORDER", "RGB")
MQTT_HOST = os.environ.get("MQTT_HOST")
MQTT_PORT = os.environ.get("MQTT_PORT")
MQTT_USERNAME = os.environ.get("MQTT_USERNAME")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")
MQTT_CA_CERT_PATH = os.environ.get("MQTT_CA_CERT_PATH", "ca.crt")

MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "10"))
BACKOFF_FACTOR = int(os.environ.get("BACKOFF_FACTOR", "2"))

## LED Settings
# Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
# NeoPixels must be connected to D10, D12, D18 or D21 to work.
pixel_pin = board.D18

# The number of NeoPixels
num_pixels = 0
try:
    num_pixels = int(LEDS_NUM)
except Exception:
    logger.error(f"Error setting led strip number of leds: {LEDS_NUM}")
    sys.exit()

pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=PIXELS_ORDER
)

children = []
strip_color = (0, 0, 0)

# terminate all child processes
# and turn off the led strip in case of
# SIGTERM or SIGINT
def terminate_process(signum, frame, mqtt_client):
    for child in children:
        os.kill(child, SIGKILL)
    rainbow_effect_stat(False)
    strip_color_stat(False)
    set_strip_availability(mqtt_client, False)
    pixels.fill((0, 0, 0))
    pixels.show()
    sys.exit(0)

# standard hsv to rgb conversion
def hsv2rgb(h,s,v):
    return tuple(round(i * 255) for i in colorsys.hsv_to_rgb(h,s,v))

# https://learn.adafruit.com/circuitpython-essentials/circuitpython-neopixel
def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b) if PIXELS_ORDER in ("RGB", "GRB", "BRG") else (r, g, b, 0)

# Define rainbow cycle function to generate
# rainbow effect on LED strip
# https://learn.adafruit.com/circuitpython-essentials/circuitpython-neopixel
def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)

# Set rainbow effect status
# and publish to MQTT
def rainbow_effect_stat(on = True):
    status = b'ON'
    if (on != True):
        for child in children:
            os.kill(child, SIGKILL)
        pixels.fill((0, 0, 0))
        pixels.show()
        status = b'OFF'
    client.publish(f"stat/{DEVICE_ID}/effects/rainbow", status)

def strip_color_stat(on = True):
    status = b'ON'
    if (on != True):
        status = b'OFF'
    client.publish(f"stat/{DEVICE_ID}/POWER", status)

def set_strip_availability(client, on = True):
    status = b'Online'
    if (on != True):
        status = b'Offline'
    client.publish(f"stat/{DEVICE_ID}/STATUS", status)

# The callback function. It will be triggered when trying to connect to the MQTT broker
# client is the client instance connected this time
# userdata is users' information, usually empty. If it is needed, you can set it through user_data_set function.
# flags save the dictionary of broker response flag.
# rc is the response code.
# Generally, we only need to pay attention to whether the response code is 0.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected successfully!")
        client.subscribe(f"cmnd/{DEVICE_ID}/POWER")
        client.subscribe(f"cmnd/{DEVICE_ID}/HSBColor")
        client.subscribe(f"cmnd/{DEVICE_ID}/effects/rainbow/set")
    else:
        logger.error(f"Connected fail with code {rc}")


def on_message(client, userdata, msg):
    global strip_color
    logger.info(f"{msg.topic} {msg.payload}")
    if msg.topic == f"cmnd/{DEVICE_ID}/effects/rainbow/set":
        switch = msg.payload.decode('UTF-8')
        logger.debug(f"Setting effect: {switch}")
        strip_color_stat(False)
        if switch == "OFF":
            #Put Off
            rainbow_effect_stat(False)
        elif switch == "ON":
            #Put On
            rainbow_effect_stat()
            pid = os.fork()
            if pid > 0: children.append(pid)
            else:
                while True:
                    rainbow_cycle(0.010)
        else:
            logger.error(f"Unknown switch: {switch}")
    elif msg.topic == f"cmnd/{DEVICE_ID}/HSBColor":
        color = msg.payload.decode('UTF-8')
        rgb_color = (0, 0, 0)
        logger.debug(f"Setting HSBColor: {color}")
        try:
            hsv = color.split(",")
            rgb_color = hsv2rgb(int(hsv[0])/360, int(hsv[1])/100, int(hsv[2])/100)
            logger.debug(rgb_color)
            strip_color = rgb_color
            rainbow_effect_stat(False)
            if (strip_color == (0, 0, 0)):
                strip_color_stat(False)
            else:
                strip_color_stat(True)
            pixels.fill(strip_color)
            pixels.show()
        except Exception:
            logger.error(f"Unable to convert HSBColor to RGB")
    elif msg.topic == f"cmnd/{DEVICE_ID}/POWER":
        power = msg.payload.decode('UTF-8')
        logger.debug(f"Setting strip power: {power}")
        if power == "ON":
            rainbow_effect_stat(False)
            if (strip_color == (0, 0, 0)):
                strip_color_stat(False)
            else:
                strip_color_stat(True)
            pixels.fill(strip_color)
            pixels.show()
        else:
            strip_color_stat(False)
            pixels.fill((0, 0, 0))
            pixels.show()
    else:
        logger.error(f"Unknown topic: {msg.topic}")


def connect_with_retries(client, host, port, keepalive, max_retries=MAX_RETRIES):
    attempt = 0
    delay = 1  # start with a 1-second delay

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Set TLS ca certificate
    if MQTT_CA_CERT_PATH is not None:
        client.tls_set(ca_certs=MQTT_CA_CERT_PATH)
    client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)

    while attempt < max_retries:
        try:
            logger.info(f"Attempting to connect to {host}:{port} (Attempt {attempt + 1}/{max_retries})...")
            client.connect(MQTT_HOST, int(MQTT_PORT), 15)

            return client
        except Exception as e:
            logger.error(f"Connection failed with error: {e}. Retrying in {delay} seconds...")
            attempt += 1  # increate attempt count
            delay *= BACKOFF_FACTOR  # increase delay for the next attempt
            time.sleep(delay)

    logger.error("Max retries reached. Could not connect to MQTT broker.")
    raise ConnectionError("Failed to connect to MQTT broker after multiple retries.")


if __name__ == "__main__":
    client = None
    try:
        client = connect_with_retries(client, MQTT_HOST, int(MQTT_PORT), keepalive=15)
    except ConnectionError:
        logger.error("Error connection to MQTT server")
        exit(1)  # exit if connection could not be established

    # define signal handling
    signal(SIGTERM, lambda s, f: terminate_process(s, f, client))

    set_strip_availability(client)
    client.loop_forever()