# edge-net-gfx

A node in [Edge-NET](https://github.com/jackwaddington/edge-net). A Pi Pico W with a Pimoroni GFX Hat running MicroPython, connected to the edge-net WiFi and subscribed to MQTT topics. Displays data and status on the GFX screen.

## Hardware

- [Raspberry Pi Pico W](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html)
- [Pimoroni GFX Pack](https://shop.pimoroni.com/products/pico-gfx-pack) (small display + buttons)

## What it does

- Connects to the Edge-NET WiFi network
- Connects to the Mosquitto MQTT broker on the hub
- Subscribes to topics and displays the data on the GFX screen
- When the home network uplink is available, can pull data from Prometheus/Grafana for display

## Software

MicroPython. The Pico W must be flashed via USB to update.

## MQTT topics

| Topic | Direction | Description |
| ----- | --------- | ----------- |
| TBD | subscribe | Data to display |

## Screens

Screens are **views into a concern**, not jobs owned by this device. The GFX
node is one surface that can reflect them — the same concern may also show on
e-ink, LEDs, or an arrow. Each screen pulls from data above the bus (an MQTT
topic, or an HTTP endpoint / Prometheus when the uplink is up) and renders it.

Architecture per screen: `fetch()` (get data), `render(display)` (draw), and a
refresh `interval`. The main loop cycles screens or navigates by button. New
screens are independent — adding one shouldn't touch the others.

Salvaged from the retired `edge-display` use-case:

| Screen | Source | Shows |
| ------ | ------ | ----- |
| Cluster health | Prometheus | 3 k3s nodes up/down, CPU/mem |
| Timelapse status | smart-timelapse-pipeline | capturing? frames today, last upload |
| Pi0Cam status | Pi0Cam metrics | camera up/down, last image, uptime |
| Network overview | hub | connected devices / bandwidth |
| Weather / sun | API or local sensor | sunrise/sunset (timelapse context) |
| Custom text / alert | MQTT push | ad-hoc message to the screen |

Design notes carried over: pull don't push (systems needn't know about the
display); graceful degradation (show last-known value + a staleness indicator
if a source is unreachable); stay lightweight (Pico W has ~264 KB RAM — a k3s
API gateway can pre-format JSON if parsing on-device is too heavy).

## Part of Edge-NET

See [Edge-NET](https://github.com/jackwaddington/edge-net) for the full architecture and list of nodes.
