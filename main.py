"""edge-net-gfx — GFX Pack (Pico W, MicroPython) as an Edge-NET output node.

Ambient + interrupt: shows an idle "edge-net" screen, listens on MQTT, and when
a gamepad button is pressed it shows that button big with a matching backlight.
After IDLE_RETURN seconds with no command it drifts back to ambient.

Subscribes: edge-net/gamepad/button/#  (payloads "press" / "release")
"""

import time
import network
from gfx_pack import GfxPack
from umqtt.simple import MQTTClient
import WIFI_CONFIG as W

BROKER = "10.1.1.1"
PORT = 1883
CLIENT_ID = "edge-net-gfx"
TOPIC = b"edge-net/gamepad/button/#"
IDLE_RETURN = 30          # seconds of quiet before returning to ambient

gp = GfxPack()
display = gp.display
WIDTH, HEIGHT = display.get_bounds()
display.set_font("bitmap8")

# button name -> (label, backlight rgbw)  ; None backlight = rainbow (button Y)
COLOURS = {
    "a":      ("A", (255, 0, 0, 0)),
    "b":      ("B", (0, 255, 0, 0)),
    "x":      ("X", (0, 0, 255, 0)),
    "y":      ("Y", None),
    "start":  ("START", (255, 255, 255, 0)),
    "select": ("SELECT", (255, 120, 0, 0)),
}


def hsv(h):
    h = h % 360
    x = int(255 * (1 - abs((h / 60) % 2 - 1)))
    if h < 60:    return 255, x, 0
    if h < 120:   return x, 255, 0
    if h < 180:   return 0, 255, x
    if h < 240:   return 0, x, 255
    if h < 300:   return x, 0, 255
    return 255, 0, x


def draw(label, scale, backlight):
    if backlight is not None:
        gp.set_backlight(*backlight)
    display.set_pen(0)
    display.clear()
    display.set_pen(15)
    display.text(label, 0, 4, WIDTH, scale)
    display.update()


def status(msg):
    draw("edge-net", 3, (0, 0, 0, 25))
    display.text(msg, 0, 46, WIDTH, 2)
    display.update()


# ── WiFi ────────────────────────────────────────────────────────────────────
try:
    import rp2
    rp2.country(W.COUNTRY)
except Exception:
    pass

status("wifi...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(W.SSID, W.PSK)
t0 = time.time()
while not wlan.isconnected():
    if time.time() - t0 > 20:
        status("wifi FAIL")
        raise RuntimeError("wifi connect failed")
    time.sleep(0.3)
print("wifi ok", wlan.ifconfig()[0])

# ── MQTT ────────────────────────────────────────────────────────────────────
state = {"btn": None, "ts": 0}


def on_msg(topic, msg):
    name = topic.decode().rsplit("/", 1)[-1]
    payload = msg.decode()
    print("rx", name, payload)
    if payload == "press" and name in COLOURS:
        state["btn"] = name
        state["ts"] = time.ticks_ms()


status("mqtt...")
mqtt = MQTTClient(CLIENT_ID, BROKER, port=PORT, keepalive=60)
mqtt.set_callback(on_msg)
mqtt.connect()
mqtt.subscribe(TOPIC)
print("mqtt ok ->", BROKER)
status("ready")

# ── Main loop ───────────────────────────────────────────────────────────────
last_ping = time.ticks_ms()
hue = 0

while True:
    try:
        mqtt.check_msg()                      # non-blocking
    except OSError as e:
        print("mqtt lost, reconnect:", e)
        try:
            mqtt.connect()
            mqtt.subscribe(TOPIC)
        except Exception as e2:
            print("reconnect fail:", e2)
            time.sleep(1)

    now = time.ticks_ms()
    btn = state["btn"]

    if btn and time.ticks_diff(now, state["ts"]) < IDLE_RETURN * 1000:
        label, col = COLOURS[btn]
        scale = 6 if len(label) == 1 else 2
        if col is None:                       # Y = rainbow
            hue = (hue + 5) % 360
            draw(label, scale, hsv(hue) + (0,))
        else:
            draw(label, scale, col)
    else:
        if btn:
            state["btn"] = None
        draw("edge-net", 3, (0, 0, 0, 20))

    if time.ticks_diff(now, last_ping) > 15000:
        try:
            mqtt.ping()
        except Exception:
            pass
        last_ping = now

    time.sleep(0.03)
