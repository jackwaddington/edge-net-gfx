"""Render words into scrolling LED frames for the 10x5 serpentine strip.

Ported from edge-net-plasma/sender/textmatrix.py for on-device use.
Publishes finished frames to edge-net/gamepad/frame; strip stays dumb.
"""
import time

W, H = 10, 5
NUM = W * H

FONT = {
    "A": ["010", "101", "111", "101", "101"],
    "B": ["110", "101", "110", "101", "110"],
    "C": ["011", "100", "100", "100", "011"],
    "D": ["110", "101", "101", "101", "110"],
    "E": ["111", "100", "110", "100", "111"],
    "F": ["111", "100", "110", "100", "100"],
    "G": ["011", "100", "101", "101", "011"],
    "H": ["101", "101", "111", "101", "101"],
    "I": ["111", "010", "010", "010", "111"],
    "J": ["001", "001", "001", "101", "010"],
    "K": ["101", "101", "110", "101", "101"],
    "L": ["100", "100", "100", "100", "111"],
    "M": ["101", "111", "111", "101", "101"],
    "N": ["101", "111", "111", "111", "101"],
    "O": ["010", "101", "101", "101", "010"],
    "P": ["110", "101", "110", "100", "100"],
    "Q": ["010", "101", "101", "110", "011"],
    "R": ["110", "101", "110", "101", "101"],
    "S": ["011", "100", "010", "001", "110"],
    "T": ["111", "010", "010", "010", "010"],
    "U": ["101", "101", "101", "101", "111"],
    "V": ["101", "101", "101", "101", "010"],
    "W": ["101", "101", "111", "111", "101"],
    "X": ["101", "101", "010", "101", "101"],
    "Y": ["101", "101", "010", "010", "010"],
    "Z": ["111", "001", "010", "100", "111"],
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"],
    "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"],
    "7": ["111", "001", "010", "100", "100"],
    "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"],
    " ": ["000", "000", "000", "000", "000"],
    "-": ["000", "000", "111", "000", "000"],
    "!": ["010", "010", "010", "000", "010"],
    "?": ["110", "001", "010", "000", "010"],
}


def _columns_for(text):
    cols = []
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for c in range(3):
            cols.append([1 if glyph[r][c] == "1" else 0 for r in range(5)])
        cols.append([0, 0, 0, 0, 0])
    return cols


def _xy_to_index(x, y):
    return y * W + (x if y % 2 == 0 else (W - 1 - x))


def _frame_hex(cols, start, colour):
    px = [(0, 0, 0)] * NUM
    for x in range(W):
        col = start + x
        if 0 <= col < len(cols):
            for y in range(H):
                if cols[col][y]:
                    px[_xy_to_index(x, y)] = colour
    return "".join("%02x%02x%02x" % p for p in px)


def send_word(word, mqtt, colour=(0, 200, 255), delay_ms=60):
    """Render word to scrolling frames and stream to the dumb strip."""
    blank = [[0] * 5] * W
    cols = blank + _columns_for(word) + blank
    for start in range(len(cols) - W + 1):
        try:
            mqtt.publish(b"edge-net/gamepad/frame", _frame_hex(cols, start, colour))
        except Exception as e:
            print("frame pub err:", e)
        time.sleep_ms(delay_ms)
