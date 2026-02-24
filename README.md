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

## Part of Edge-NET

See [Edge-NET](https://github.com/jackwaddington/edge-net) for the full architecture and list of nodes.
