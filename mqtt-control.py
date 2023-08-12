# rpi - led strip controller
import os
import sys
import time
import board
import colorsys
import neopixel
import paho.mqtt.client as mqtt
from signal import SIGKILL


## MQTT Settings
DEVICE_ID = os.environ.get('DEVICE_ID', 'rpi4_debug')
LEDS_NUM = os.environ.get('LEDS_NUM')
MQTT_HOST = os.environ.get('MQTT_HOST')
MQTT_PORT = os.environ.get('MQTT_PORT')
MQTT_USERNAME = os.environ.get('MQTT_USERNAME')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD')

client = mqtt.Client()

## LED Settings
# Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
# NeoPixels must be connected to D10, D12, D18 or D21 to work.
pixel_pin = board.D18

# The number of NeoPixels
num_pixels = 0
try:
    num_pixels = int(LEDS_NUM)
except Exception:
    print(f"Error setting led strip number of leds: {LEDS_NUM}")
    sys.exit()


# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.RGB

pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=ORDER
)

children = []
strip_color = (0, 0, 0)

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
    return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)

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


# The callback function. It will be triggered when trying to connect to the MQTT broker
# client is the client instance connected this time
# userdata is users' information, usually empty. If it is needed, you can set it through user_data_set function.
# flags save the dictionary of broker response flag.
# rc is the response code.
# Generally, we only need to pay attention to whether the response code is 0.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected success")
        client.subscribe(f"cmnd/{DEVICE_ID}/POWER")
        client.subscribe(f"cmnd/{DEVICE_ID}/HSBColor")
        client.subscribe(f"cmnd/{DEVICE_ID}/effects/rainbow/set")
    else:
        print(f"Connected fail with code {rc}")


def on_message(client, userdata, msg):
    global strip_color
    print(f"{msg.topic} {msg.payload}")
    if msg.topic == f"cmnd/{DEVICE_ID}/effects/rainbow/set":
        switch = msg.payload.decode('UTF-8')
        print(f"Setting effect: {switch}")
        client.publish(f"stat/{DEVICE_ID}/POWER", b'OFF')
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
            print(f"Unknown switch: {switch}")
    elif msg.topic == f"cmnd/{DEVICE_ID}/HSBColor":
        color = msg.payload.decode('UTF-8')
        rgb_color = (0, 0, 0)
        print(f"Setting HSBColor: {color}")
        try:
            hsv = color.split(",")
            rgb_color = hsv2rgb(int(hsv[0])/360, int(hsv[1])/100, int(hsv[2])/100)
            print(rgb_color)
            strip_color = rgb_color
            rainbow_effect_stat(False)
            pixels.fill(strip_color)
            pixels.show()
        except Exception:
            print(f"Unable to convert HSBColor to RGB")
    elif msg.topic == f"cmnd/{DEVICE_ID}/POWER":
        power = msg.payload.decode('UTF-8')
        print(f"Setting strip power: {power}")
        if power == "ON":
            rainbow_effect_stat(False)
            pixels.fill(strip_color)
            pixels.show()
        else:
            pixels.fill((0, 0, 0))
            pixels.show()
    else:
        print(f"Unknown topic: {msg.topic}")


client.on_connect = on_connect
client.on_message = on_message


client.tls_set(ca_certs="ca.crt")
client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)
print(f"Connecting to {MQTT_HOST}:{MQTT_PORT}...")
client.connect(MQTT_HOST, int(MQTT_PORT), 15) 
client.loop_forever()
