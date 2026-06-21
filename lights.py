"""Light Control mode — three pages: colour, effect, speed.

The GFX backlight previews the selected effect live; on SEND the same
animation streams as frames to the dumb strip. Strip never runs logic —
it just blits whatever frames arrive.
"""
import random

COLOURS = [
    ("RED",     (200,   0,   0)),
    ("GREEN",   (  0, 200,   0)),
    ("BLUE",    (  0,   0, 200)),
    ("CYAN",    (  0, 160, 200)),
    ("PURPLE",  (140,   0, 200)),
    ("YELLOW",  (200, 140,   0)),
    ("ORANGE",  (200,  60,   0)),
    ("WHITE",   (180, 180, 180)),
]

EFFECTS = ["SOLID", "FLASH", "RAINBOW", "RANDOM"]
SPEED_NAMES = ["SLOW", "MED", "FAST"]
SPEED_MS = [600, 200, 80]

NUM_LEDS = 50


def _hsv(h):
    h = h % 360
    x = int(255 * (1 - abs((h / 60) % 2 - 1)))
    if h < 60:   return 255, x, 0
    if h < 120:  return x, 255, 0
    if h < 180:  return 0, 255, x
    if h < 240:  return 0, x, 255
    if h < 300:  return x, 0, 255
    return 255, 0, x


class LightsMode:
    def __init__(self):
        self.page = 0
        self.colour_idx = 0
        self.effect_idx = 0
        self.speed_idx = 1
        self.broadcasting = False
        self._hue = 0
        self._flash_on = True

    def reset(self):
        self.page = 0
        self.broadcasting = False
        self._hue = 0
        self._flash_on = True

    def colour(self):
        return COLOURS[self.colour_idx][1]

    def effect(self):
        return EFFECTS[self.effect_idx]

    def frame_ms(self):
        return SPEED_MS[self.speed_idx]

    def scroll(self, delta):
        if self.page == 0:
            self.colour_idx = (self.colour_idx + delta) % len(COLOURS)
        elif self.page == 1:
            self.effect_idx = (self.effect_idx + delta) % len(EFFECTS)
        else:
            self.speed_idx = (self.speed_idx + delta) % len(SPEED_NAMES)

    def tick(self):
        self._hue = (self._hue + 8) % 360
        self._flash_on = not self._flash_on

    def preview_backlight(self):
        """RGB for GFX backlight (dim, mirrors current animation state)."""
        ef = self.effect()
        r, g, b = self.colour()
        if ef == "SOLID":
            return r // 4, g // 4, b // 4
        if ef == "FLASH":
            return (r // 4, g // 4, b // 4) if self._flash_on else (0, 0, 0)
        rr, rg, rb = _hsv(self._hue)
        return rr // 4, rg // 4, rb // 4

    def next_strip_frame(self):
        """300-char hex frame for the dumb strip; advances animation state."""
        r, g, b = self.colour()
        ef = self.effect()
        if ef == "SOLID":
            frame = "%02x%02x%02x" % (r, g, b) * NUM_LEDS
        elif ef == "FLASH":
            px = "%02x%02x%02x" % (r, g, b) if self._flash_on else "000000"
            frame = px * NUM_LEDS
        elif ef == "RAINBOW":
            frame = "".join("%02x%02x%02x" % _hsv((self._hue + i * 7) % 360)
                            for i in range(NUM_LEDS))
        else:  # RANDOM
            rr = random.randint(0, 255)
            rg = random.randint(0, 255)
            rb = random.randint(0, 255)
            frame = "%02x%02x%02x" % (rr, rg, rb) * NUM_LEDS
        self.tick()
        return frame

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, display, w):
        display.set_pen(0)
        display.clear()
        display.set_pen(15)
        display.set_font("bitmap8")
        if self.page == 0:
            self._draw_colour(display, w)
        elif self.page == 1:
            self._draw_effect(display, w)
        else:
            self._draw_speed(display, w)
        display.update()

    def draw_live(self, display, w):
        display.set_pen(0)
        display.clear()
        display.set_pen(15)
        display.set_font("bitmap8")
        display.text("LIVE", 0, 8, w, 4)
        display.text(self.effect() + " " + COLOURS[self.colour_idx][0], 0, 46, w, 2)
        display.text("SELECT=stop", 0, 56, w, 1)
        display.update()

    def _draw_colour(self, display, w):
        display.text("COLOUR  1/3", 0, 0, w, 1)
        display.line(0, 10, w - 1, 10)
        display.text(COLOURS[self.colour_idx][0], 0, 14, w, 3)
        display.text("< joy >   A=next", 0, 56, w, 1)

    def _draw_effect(self, display, w):
        display.text("EFFECT  2/3", 0, 0, w, 1)
        display.line(0, 10, w - 1, 10)
        display.text(EFFECTS[self.effect_idx], 0, 14, w, 3)
        display.text("< joy >  A=next  B=back", 0, 56, w, 1)

    def _draw_speed(self, display, w):
        display.text("SPEED   3/3", 0, 0, w, 1)
        display.line(0, 10, w - 1, 10)
        display.text(SPEED_NAMES[self.speed_idx], 0, 14, w, 3)
        display.text("< joy >  A=SEND  B=back", 0, 56, w, 1)
