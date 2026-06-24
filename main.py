"""edge-net-gfx — GFX Pack handheld with GamepadQT (I2C seesaw).

Modes (joystick Y to navigate menu, GamepadQT A/START to enter):
  SNAKE       — classic snake on 128x64 LCD, joystick steers
  TEXT        — compose a word, joystick X scrolls alphabet, send to LED strip
  LIGHTS      — 3-page wizard: colour → effect → speed; backlight mirrors strip
  CHESS       — chess clock; GFX-A = P1, GFX-E = P2, C = pause, D = reset

GFX Pack buttons A-E still publish to edge-net/gfx/button/<a-e> as before
(except A/C/D/E are intercepted in CHESS mode).
GamepadQT SELECT returns to menu from any mode.

Hardware note: STEMMA QT on GFX Pack -> I2C0, SDA=GP4, SCL=GP5.
If I2C init fails, check this against the actual Pimoroni GFX Pack pinout.
"""

import time
import network
from machine import I2C, Pin
from gfx_pack import GfxPack, SWITCH_A, SWITCH_B, SWITCH_C, SWITCH_D, SWITCH_E
from umqtt.simple import MQTTClient
import WIFI_CONFIG as W

import seesaw
import textmatrix
from snake import Snake
from lights import LightsMode
import ujson
from chess_clock import ChessClock

# ── Hardware ────────────────────────────────────────────────────────────────
# STEMMA QT connector: I2C0 on GP4 (SDA) / GP5 (SCL)
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100000)
seesaw.init(i2c)

gp = GfxPack()
display = gp.display
LCD_W, LCD_H = display.get_bounds()   # 128, 64
display.set_font("bitmap8")

LOCAL_BUTTONS = {
    "a": SWITCH_A, "b": SWITCH_B, "c": SWITCH_C, "d": SWITCH_D, "e": SWITCH_E,
}
local_state = {n: False for n in LOCAL_BUTTONS}

# ── Helpers ─────────────────────────────────────────────────────────────────
def lcd_msg(line1, line2=""):
    display.set_pen(0)
    display.clear()
    display.set_pen(15)
    display.text(line1, 0, 4, LCD_W, 2)
    if line2:
        display.text(line2, 0, 36, LCD_W, 2)
    display.update()


# ── WiFi ────────────────────────────────────────────────────────────────────
try:
    import rp2
    rp2.country(W.COUNTRY)
except Exception:
    pass

lcd_msg("wifi...")
gp.set_backlight(0, 0, 0, 25)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(W.SSID, W.PSK)
t0 = time.time()
while not wlan.isconnected():
    if time.time() - t0 > 25:
        lcd_msg("wifi", "FAIL")
        raise RuntimeError("wifi connect failed")
    time.sleep(0.3)
print("wifi ok", wlan.ifconfig()[0])

# ── MQTT ────────────────────────────────────────────────────────────────────
BROKER = "10.1.1.1"
PORT = 1883
CLIENT_ID = "edge-net-gfx"

lcd_msg("mqtt...")
mqtt = MQTTClient(CLIENT_ID, BROKER, port=PORT, keepalive=60)
mqtt.connect()
print("mqtt ok ->", BROKER)

# ── Joystick helpers ────────────────────────────────────────────────────────
JOY_LO, JOY_HI = 300, 700


def joy_dir(jx, jy):
    dx = -1 if jx < JOY_LO else (1 if jx > JOY_HI else 0)
    dy = -1 if jy < JOY_LO else (1 if jy > JOY_HI else 0)
    return dx, dy


def new_press(cur, prev, pin):
    bit = 1 << pin
    return bool((cur & bit) and not (prev & bit))


# ── Mode constants ──────────────────────────────────────────────────────────
MENU = 0
SNAKE_MODE = 1
TEXT_MODE = 2
LIGHTS_MODE = 3
CHESS_MODE = 4

MENU_ITEMS = ["SNAKE", "TEXT", "LIGHTS", "CHESS"]
MENU_VISIBLE = 3   # items shown at once (3 × 20px fits 64px display)
SNAKE_TICK = 150   # ms per snake step
JOY_REPEAT = 250   # ms between repeated nav/scroll triggers

# ── Menu draw ───────────────────────────────────────────────────────────────
def draw_menu(sel, offset):
    display.set_pen(0)
    display.clear()
    display.set_pen(15)
    visible = MENU_ITEMS[offset:offset + MENU_VISIBLE]
    for i, name in enumerate(visible):
        prefix = "> " if (offset + i) == sel else "  "
        display.text(prefix + name, 2, 2 + i * 20, LCD_W - 12, 2)
    if offset > 0:
        display.text("^", LCD_W - 10, 2, 10, 1)
    if offset + MENU_VISIBLE < len(MENU_ITEMS):
        display.text("v", LCD_W - 10, 54, 10, 1)
    display.update()


# ── Text composer ────────────────────────────────────────────────────────────
ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789!?"
MAX_WORD = 15

char_idx = 0
word = []


def draw_text():
    display.set_pen(0)
    display.clear()
    display.set_pen(15)
    word_str = "".join(word) if word else "-"
    display.text(word_str, 0, 0, LCD_W, 1)
    display.line(0, 10, LCD_W - 1, 10)
    ch = ALPHA[char_idx]
    display.text(ch, (LCD_W - 32) // 2, 13, LCD_W, 4)
    display.text("A=add  B=del  ST=send", 0, 56, LCD_W, 1)
    display.update()


# ── Snake ────────────────────────────────────────────────────────────────────
snake = Snake()
snake_ts = 0

# ── Lights ───────────────────────────────────────────────────────────────────
lights = LightsMode()
lights_frame_ts = 0

# ── Chess clock ──────────────────────────────────────────────────────────────
chess = ChessClock()

# ── State ────────────────────────────────────────────────────────────────────
mode = MENU
prev_mode = -1
menu_sel = 0
menu_offset = 0
prev_gp_btns = 0
joy_nav_ts = 0      # last joystick nav repeat (menu + text scroll)
chess_draw_ts = 0
last_ping = time.ticks_ms()

# ── Chess helpers ────────────────────────────────────────────────────────────
_P1_FRAME = b"FF6600" * 50   # warm orange for P1 on LED strip
_P2_FRAME = b"0066FF" * 50   # cool blue  for P2 on LED strip


def _chess_publish(kind, player):
    p_str = "p1" if player == 0 else "p2"
    try:
        mqtt.publish("edge-net/gfx/chess/" + kind, ujson.dumps({"player": p_str}))
    except Exception:
        pass
    sounds = {"start": "chime.wav", "switch": "tick.wav",
              "flag": "flag.wav", "warning": "warning.wav"}
    if kind in sounds:
        try:
            mqtt.publish("edge/hub/audio/play", ujson.dumps({"file": sounds[kind]}))
        except Exception:
            pass
    if kind in ("start", "switch"):
        frame = _P1_FRAME if chess.active == 0 else _P2_FRAME
        try:
            mqtt.publish(b"edge-net/gamepad/frame", frame)
        except Exception:
            pass


def _chess_btn(player):
    ev = chess.press(player)
    if ev is None:
        return
    r, g, b, w = chess.backlight_rgb()
    gp.set_backlight(r, g, b, w)
    chess.draw(display, LCD_W)
    _chess_publish(ev, player)


# ── Main loop ────────────────────────────────────────────────────────────────
while True:
    now = time.ticks_ms()

    # MQTT keepalive
    try:
        mqtt.check_msg()
    except OSError:
        try:
            mqtt.connect()
        except Exception:
            pass
    if time.ticks_diff(now, last_ping) > 15000:
        try:
            mqtt.ping()
        except Exception:
            pass
        last_ping = now

    # GFX Pack own buttons -> publish edge-to-edge (chess mode intercepts A/C/D/E)
    for name, sw in LOCAL_BUTTONS.items():
        pressed = gp.switch_pressed(sw)
        if pressed != local_state[name]:
            local_state[name] = pressed
            if mode == CHESS_MODE and name in ("a", "c", "d", "e"):
                if pressed:
                    if name == "a":
                        _chess_btn(0)
                    elif name == "e":
                        _chess_btn(1)
                    elif name == "c":
                        chess.pause_toggle()
                        r, g, b, w = chess.backlight_rgb()
                        gp.set_backlight(r, g, b, w)
                        chess.draw(display, LCD_W)
                    elif name == "d":
                        chess.reset()
                        r, g, b, w = chess.backlight_rgb()
                        gp.set_backlight(r, g, b, w)
                        chess.draw(display, LCD_W)
            else:
                ev = "press" if pressed else "release"
                try:
                    mqtt.publish("edge-net/gfx/button/" + name, ev)
                except Exception:
                    pass

    # Read GamepadQT (fallback on I2C error: no change)
    try:
        cur_btns = seesaw.read_buttons(i2c)
        jx, jy = seesaw.read_joy(i2c)
    except Exception:
        cur_btns = prev_gp_btns
        jx, jy = 512, 512

    dx, dy = joy_dir(jx, jy)

    # ── Mode entry ──────────────────────────────────────────────────────────
    if mode != prev_mode:
        if mode == MENU:
            gp.set_backlight(0, 0, 0, 80)
            draw_menu(menu_sel, menu_offset)
        elif mode == SNAKE_MODE:
            gp.set_backlight(0, 25, 0, 0)
            snake.reset()
            snake_ts = now
            snake.draw(display)
        elif mode == TEXT_MODE:
            gp.set_backlight(0, 0, 25, 0)
            word.clear()
            char_idx = 0
            draw_text()
        elif mode == LIGHTS_MODE:
            lights.reset()
            lights_frame_ts = now
            lights.draw(display, LCD_W)
            pr, pg, pb = lights.preview_backlight()
            gp.set_backlight(pr, pg, pb, 0)
        elif mode == CHESS_MODE:
            chess.reset()
            chess_draw_ts = now
            r, g, b, w = chess.backlight_rgb()
            gp.set_backlight(r, g, b, w)
            chess.draw(display, LCD_W)
        prev_mode = mode

    # ── SELECT -> menu (any mode); stop lights broadcast if active ─────────
    if new_press(cur_btns, prev_gp_btns, 0):   # pin 0 = select
        if mode == LIGHTS_MODE and lights.broadcasting:
            lights.broadcasting = False
            try:
                mqtt.publish(b"edge-net/gamepad/led/clear", b"")
            except Exception:
                pass
        mode = MENU

    # ── Mode logic ──────────────────────────────────────────────────────────
    elif mode == MENU:
        nav_ready = time.ticks_diff(now, joy_nav_ts) > JOY_REPEAT
        if nav_ready and dy == -1:
            menu_sel = (menu_sel - 1) % len(MENU_ITEMS)
            if menu_sel < menu_offset:
                menu_offset = menu_sel
            draw_menu(menu_sel, menu_offset)
            joy_nav_ts = now
        elif nav_ready and dy == 1:
            menu_sel = (menu_sel + 1) % len(MENU_ITEMS)
            if menu_sel >= menu_offset + MENU_VISIBLE:
                menu_offset = menu_sel - MENU_VISIBLE + 1
            if menu_sel == 0:           # wrapped around to top
                menu_offset = 0
            draw_menu(menu_sel, menu_offset)
            joy_nav_ts = now
        # A (pin 5) or START (pin 16) confirm
        if new_press(cur_btns, prev_gp_btns, 5) or new_press(cur_btns, prev_gp_btns, 16):
            mode = [SNAKE_MODE, TEXT_MODE, LIGHTS_MODE, CHESS_MODE][menu_sel]

    elif mode == SNAKE_MODE:
        snake.steer(dx, -dy)
        if time.ticks_diff(now, snake_ts) >= SNAKE_TICK:
            snake.step()
            snake.draw(display)
            snake_ts = now
            if not snake.alive:
                gp.set_backlight(25, 0, 0, 0)
        # A = restart after death
        if not snake.alive and new_press(cur_btns, prev_gp_btns, 5):
            gp.set_backlight(0, 25, 0, 0)
            snake.reset()
            snake_ts = now

    elif mode == TEXT_MODE:
        nav_ready = time.ticks_diff(now, joy_nav_ts) > JOY_REPEAT
        if nav_ready and dx == -1:
            char_idx = (char_idx - 1) % len(ALPHA)
            draw_text()
            joy_nav_ts = now
        elif nav_ready and dx == 1:
            char_idx = (char_idx + 1) % len(ALPHA)
            draw_text()
            joy_nav_ts = now
        if new_press(cur_btns, prev_gp_btns, 5):    # A = add letter
            if len(word) < MAX_WORD:
                word.append(ALPHA[char_idx])
            draw_text()
        if new_press(cur_btns, prev_gp_btns, 1):    # B = backspace
            if word:
                word.pop()
            draw_text()
        if new_press(cur_btns, prev_gp_btns, 16):   # START = send to strip
            if word:
                w_str = "".join(word)
                lcd_msg("sending...", w_str[:15])
                gp.set_backlight(50, 50, 0, 0)
                textmatrix.send_word(w_str, mqtt)
                gp.set_backlight(0, 0, 25, 0)
                draw_text()

    elif mode == LIGHTS_MODE:
        if lights.broadcasting:
            if time.ticks_diff(now, lights_frame_ts) >= lights.frame_ms():
                frame = lights.next_strip_frame()
                try:
                    mqtt.publish(b"edge-net/gamepad/frame", frame)
                except Exception:
                    pass
                pr, pg, pb = lights.preview_backlight()
                gp.set_backlight(pr, pg, pb, 0)
                lights_frame_ts = now
        else:
            # Preview animation on backlight at a fixed rate
            if time.ticks_diff(now, lights_frame_ts) >= 200:
                lights.tick()
                pr, pg, pb = lights.preview_backlight()
                gp.set_backlight(pr, pg, pb, 0)
                lights_frame_ts = now

            nav_ready = time.ticks_diff(now, joy_nav_ts) > JOY_REPEAT
            if nav_ready and dx == -1:
                lights.scroll(-1)
                lights.draw(display, LCD_W)
                joy_nav_ts = now
            elif nav_ready and dx == 1:
                lights.scroll(1)
                lights.draw(display, LCD_W)
                joy_nav_ts = now

            if new_press(cur_btns, prev_gp_btns, 5):    # A = next page / send
                if lights.page < 2:
                    lights.page += 1
                    lights.draw(display, LCD_W)
                else:
                    lights.broadcasting = True
                    lights_frame_ts = 0
                    lights.draw_live(display, LCD_W)
            if new_press(cur_btns, prev_gp_btns, 1):    # B = back a page
                if lights.page > 0:
                    lights.page -= 1
                    lights.draw(display, LCD_W)

    elif mode == CHESS_MODE:
        ev = chess.update()
        if ev is not None:
            kind, player = ev
            r, g, b, w = chess.backlight_rgb()
            gp.set_backlight(r, g, b, w)
            chess.draw(display, LCD_W)
            _chess_publish(kind, player)
            chess_draw_ts = now
        elif chess.active != -1 and not chess.paused:
            if time.ticks_diff(now, chess_draw_ts) >= 1000:
                chess.draw(display, LCD_W)
                chess_draw_ts = now

    prev_gp_btns = cur_btns
    time.sleep_ms(30)
