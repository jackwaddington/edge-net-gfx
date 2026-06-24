import time


class ChessClock:
    DEFAULT_SECS = 300  # 5 minutes each

    def __init__(self):
        self.time = [self.DEFAULT_SECS, self.DEFAULT_SECS]
        self.active = -1        # -1=idle, 0=P1 clock running, 1=P2 clock running
        self.paused = False
        self.flagged = -1       # -1=none, else which player ran out
        self._last_ms = 0
        self._warned = [False, False]

    def press(self, player):
        """Player 0 (A) or 1 (E) hits their button. Returns event str or None."""
        if self.flagged >= 0:
            return None
        if self.active == -1:
            # First press starts opponent's clock (standard chess clock)
            self.active = 1 - player
            self.paused = False
            self._last_ms = time.ticks_ms()
            return "start"
        if self.paused or self.active != player:
            return None
        self.active = 1 - player
        self._last_ms = time.ticks_ms()
        return "switch"

    def pause_toggle(self):
        if self.active == -1 or self.flagged >= 0:
            return
        self.paused = not self.paused
        if not self.paused:
            self._last_ms = time.ticks_ms()

    def reset(self):
        self.__init__()

    def update(self):
        """Call each loop tick. Returns ("flag", p), ("warning", p), or None."""
        if self.active == -1 or self.paused or self.flagged >= 0:
            return None
        now = time.ticks_ms()
        elapsed_ms = time.ticks_diff(now, self._last_ms)
        if elapsed_ms < 1000:
            return None
        secs = elapsed_ms // 1000
        self._last_ms = time.ticks_add(self._last_ms, secs * 1000)
        self.time[self.active] -= secs
        if self.time[self.active] <= 0:
            self.time[self.active] = 0
            self.flagged = self.active
            self.active = -1
            return ("flag", self.flagged)
        if self.time[self.active] <= 60 and not self._warned[self.active]:
            self._warned[self.active] = True
            return ("warning", self.active)
        return None

    @staticmethod
    def fmt(secs):
        if secs < 0:
            secs = 0
        return "{:02d}:{:02d}".format(secs // 60, secs % 60)

    def draw(self, display, LCD_W):
        display.set_pen(0)
        display.clear()
        for p in range(2):
            y = p * 32
            is_active = (self.active == p)
            is_flagged = (self.flagged == p)
            if is_active:
                display.set_pen(15)
                display.rectangle(0, y, LCD_W, 31)
                tp = 0
            else:
                tp = 15
            display.set_pen(tp)
            label = "P1" if p == 0 else "P2"
            display.text(label, 2, y + 8, 18, 1)
            t_str = "FLAG!" if is_flagged else self.fmt(self.time[p])
            display.text(t_str, 22, y + 8, LCD_W - 34, 2)
            if is_active and not self.paused:
                display.text(">", LCD_W - 10, y + 8, 10, 1)
            elif self.paused and is_active:
                display.text("II", LCD_W - 16, y + 6, 14, 1)
        display.set_pen(15)
        display.line(0, 31, LCD_W - 1, 31)
        display.update()

    def backlight_rgb(self):
        """Returns (r, g, b, w) for gp.set_backlight()."""
        if self.flagged >= 0:
            return (100, 0, 0, 0)
        if self.active == -1:
            return (0, 0, 0, 20)
        if self.paused:
            return (0, 0, 0, 10)
        if self._warned[self.active]:
            return (80, 0, 0, 0)
        return (50, 20, 0, 0) if self.active == 0 else (0, 20, 50, 0)
