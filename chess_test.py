"""Standalone chess clock test — no WiFi, no MQTT."""
import time
from gfx_pack import GfxPack, SWITCH_A, SWITCH_B, SWITCH_C, SWITCH_D, SWITCH_E
from chess_clock import ChessClock

gp = GfxPack()
display = gp.display
LCD_W, _ = display.get_bounds()
display.set_font("bitmap8")

chess = ChessClock()
btn_state = {SWITCH_A: False, SWITCH_B: False, SWITCH_C: False,
             SWITCH_D: False, SWITCH_E: False}

gp.set_backlight(0, 0, 0, 80)
chess.draw(display, LCD_W)
draw_ts = time.ticks_ms()

while True:
    now = time.ticks_ms()
    ev = chess.update()
    if ev is not None:
        kind, player = ev
        r, g, b, w = chess.backlight_rgb()
        gp.set_backlight(r, g, b, w)
        chess.draw(display, LCD_W)
        draw_ts = now
    elif chess.active != -1 and not chess.paused:
        if time.ticks_diff(now, draw_ts) >= 1000:
            chess.draw(display, LCD_W)
            draw_ts = now

    for sw, was_pressed in list(btn_state.items()):
        pressed = gp.switch_pressed(sw)
        if pressed != was_pressed:
            btn_state[sw] = pressed
            if pressed:
                if sw == SWITCH_A:
                    chess.press(0)
                elif sw == SWITCH_E:
                    chess.press(1)
                elif sw == SWITCH_C:
                    chess.pause_toggle()
                elif sw == SWITCH_D:
                    chess.reset()
                    gp.set_backlight(0, 0, 0, 80)
                r, g, b, w = chess.backlight_rgb()
                gp.set_backlight(r, g, b, w)
                chess.draw(display, LCD_W)

    time.sleep_ms(30)
