# Edge-NET — GFX handheld build brief

A self-contained brief for an agent (or a future session) to build the GFX into a
handheld controller/composer. Doubles as a project overview.

## What Edge-NET is

A standalone, internet-free IoT mesh. A Raspberry Pi hub (OpenBSD) runs its own
WiFi AP (SSID `Pirie`, password in the **edge-net-secrets** repo) on 10.1.1.0/24,
plus a Mosquitto MQTT broker at **10.1.1.1:1883**. All nodes talk ONLY via MQTT.
Core principle: **dumb nodes, smart edge** — devices send/parse simple messages;
intelligence lives above the bus. Displays are dumb renderers that show what
they're told. Repos live under `~/github/`: `edge-net` (umbrella + `docs/`),
`edge-net-gfx`, `edge-net-plasma`, `edge-net-gamepad`, `edge-net-automation`,
`edge-net-hub`, `edge-net-secrets`.

## Relevant current state

- **LED STRIP** = a Plasma Stick 2040W (CircuitPython) running a DUMB FRAMEBUFFER:
  subscribes `edge-net/gamepad/frame` and blits raw pixels. Frame format = a hex
  string, 6 chars/pixel `RRGGBB`, 50 px = 300 chars. Also takes
  `edge-net/gamepad/led` (`r,g,b` solid) and `.../led/clear`. Repo: `edge-net-plasma`.
  A text renderer ALREADY EXISTS at `edge-net-plasma/sender/textmatrix.py` — renders
  a word into scrolling frames for a 10×5 SERPENTINE matrix with a 3×5 font. Study
  it; reuse its logic.
- **GFX** = Pimoroni GFX Pack on a Pi Pico W, MicroPython. Repo: `edge-net-gfx`.
  Current `main.py`: connects WiFi (`WIFI_CONFIG.py`), subscribes
  `edge-net/gamepad/button/#` and shows the pressed button on its 128×64 mono LCD +
  colour backlight; publishes its own 5 GFX-Pack buttons as
  `edge-net/gfx/button/<a-e>`. Uses `gfx_pack` (PicoGraphics) and `umqtt.simple`
  (already in `lib/`).
- **GAMEPADQT** = Adafruit Mini I2C Gamepad (seesaw, I2C addr `0x50`), now plugged
  into the GFX's STEMMA QT port. The GFX does NOT read it yet. The seesaw protocol
  (button bitmask + joystick ADC) is implemented in CircuitPython in
  `edge-net-gamepad/code.py` — READ IT for the register details: buttons on seesaw
  GPIO 0,1,2,5,6,16 = select,b,y,a,x,start (LOW=pressed); joystick on ADC channels
  14,15 (0–1023, centre ~512). Port this to MicroPython (`machine.I2C`). VERIFY the
  GFX Pack's QT I2C bus + SDA/SCL pins from the Pimoroni pinout first.

## Task: turn the GFX into a handheld

New GFX firmware (MicroPython) that reads the GamepadQT and adds:

1. A **mode menu** (joystick to choose): e.g. SNAKE and TEXT.
2. **SNAKE** — a small joystick game on the 128×64 LCD (`snake.py` is in the GFX
   examples as a starting point).
3. **TEXT COMPOSER** — joystick scrolls the alphabet, a button adds a letter (build
   a word shown on the LCD), another button SENDS. On send, render the word to
   scrolling frames (reuse the serpentine 10×5 + 3×5 logic from
   `edge-net-plasma/sender/textmatrix.py`) and stream them to
   `edge-net/gamepad/frame` so the strip scrolls the word. Keep publishing the GFX's
   own buttons as now.

Keep the dumb-strip principle: the GFX renders + streams finished frames; the strip
stays dumb.

## Flash + test mechanics

- GFX is a MicroPython Pico W; mounts as a serial port (no drive), e.g.
  `/dev/cu.usbmodem*` on macOS. Use `mpremote` (in the `python_school` venv):
  `mpremote connect <port> fs cp main.py :main.py`; reboot via serial ctrl-C then
  ctrl-D, or `mpremote reset`. To read behaviour, capture the serial port with a
  background pyserial loop so the user can interact, then read the log.
- `umqtt.simple` is already in the GFX's `lib/`. `WIFI_CONFIG.py` = SSID `Pirie` +
  the real PSK (gitignored). Broker 10.1.1.1:1883.
- The dev Mac is NOT on the AP — it can't reach the broker directly. To inspect
  MQTT, go via the hub: `ssh hub` then `mosquitto_pub`/`mosquitto_sub` against
  10.1.1.1. (Hub is OpenBSD: no python3, but fractional `sleep` works.)

## Gotchas

- MicroPython (`machine.I2C`) vs CircuitPython (`busio`) I2C APIs differ; the seesaw
  register reads in `edge-net-gamepad/code.py` are the protocol reference — adapt
  the calls.
- GFX-Pack buttons (`SWITCH_A..E` via `gfx_pack`) are SEPARATE from the GamepadQT
  buttons (over I2C). Don't conflate.
- WiFi association on these boards can take ~15–20s; don't interrupt mid-connect.
- Commit convention: `WIFI_CONFIG.py` / `config.py` are gitignored; `*.example.py`
  templates are committed; real secrets only in `edge-net-secrets` + on device.

**Deliver:** new `edge-net-gfx/main.py` (+ helper modules), tested on the device,
committed.
