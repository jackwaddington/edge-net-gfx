"""Snake game for 128x64 mono LCD (PicoGraphics / GFX Pack)."""
import random

CELL = 4       # pixels per cell
COLS = 32      # 128 // CELL
ROWS = 16      # 64 // CELL


def _rand_food(body_set):
    while True:
        pos = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
        if pos not in body_set:
            return pos


class Snake:
    def __init__(self):
        self.reset()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.body = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.dx, self.dy = 1, 0
        self.food = _rand_food(set(self.body))
        self.alive = True
        self.score = 0

    def steer(self, dx, dy):
        if dx == -self.dx and dy == -self.dy:
            return  # no 180° reversal
        if dx != 0 or dy != 0:
            self.dx, self.dy = dx, dy

    def step(self):
        if not self.alive:
            return
        hx, hy = self.body[0]
        nx, ny = hx + self.dx, hy + self.dy
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            self.alive = False
            return
        body_set = set(self.body)
        if (nx, ny) in body_set:
            self.alive = False
            return
        self.body.insert(0, (nx, ny))
        if (nx, ny) == self.food:
            self.score += 1
            body_set.add((nx, ny))
            self.food = _rand_food(body_set)
        else:
            self.body.pop()

    def draw(self, display):
        display.set_pen(0)
        display.clear()
        display.set_pen(15)
        for x, y in self.body:
            display.rectangle(x * CELL, y * CELL, CELL - 1, CELL - 1)
        fx, fy = self.food
        display.rectangle(fx * CELL + 1, fy * CELL + 1, CELL - 2, CELL - 2)
        if not self.alive:
            display.set_pen(0)
            display.rectangle(20, 22, 88, 20)
            display.set_pen(15)
            display.set_font("bitmap8")
            display.text("DEAD  +" + str(self.score), 24, 26, 90, 2)
        display.update()
