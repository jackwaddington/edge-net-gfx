"""MicroPython driver for Adafruit Mini I2C Gamepad (seesaw, addr 0x50).

Ported from edge-net-gamepad/code.py (CircuitPython busio -> machine.I2C).
Protocol reference: seesaw base 0x01 = GPIO, base 0x09 = ADC.
"""
import struct
import time

ADDR = 0x50

# seesaw GPIO pin -> button name
BUTTONS = {0: "select", 1: "b", 2: "y", 5: "a", 6: "x", 16: "start"}

_ALL = 0
for _p in BUTTONS:
    _ALL |= 1 << _p

ADC_X = 14
ADC_Y = 15


def _write(i2c, base, reg, data=b""):
    i2c.writeto(ADDR, bytes([base, reg]) + bytes(data))
    time.sleep_ms(1)


def _read(i2c, base, reg, n):
    i2c.writeto(ADDR, bytes([base, reg]))
    time.sleep_ms(1)
    return i2c.readfrom(ADDR, n)


def init(i2c):
    _write(i2c, 0x01, 0x03, struct.pack(">I", _ALL))  # DIRCLR: set all as inputs
    _write(i2c, 0x01, 0x0B, struct.pack(">I", _ALL))  # PULLENSET: enable pull-ups


def read_buttons(i2c):
    """Bitmask of currently pressed buttons (1=pressed), same pin numbering as BUTTONS."""
    raw = struct.unpack(">I", _read(i2c, 0x01, 0x04, 4))[0]
    return (~raw) & _ALL


def read_joy(i2c):
    """Returns (x, y) each 0-1023, centre ~512. Inverted to match CircuitPython driver."""
    x = 1023 - struct.unpack(">H", _read(i2c, 0x09, 0x07 + ADC_X, 2))[0]
    y = 1023 - struct.unpack(">H", _read(i2c, 0x09, 0x07 + ADC_Y, 2))[0]
    return x, y


def btn_name(pin):
    return BUTTONS.get(pin, "?")


def is_pressed(btns, pin):
    return bool(btns & (1 << pin))
