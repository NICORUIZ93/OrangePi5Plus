"""Controla los LEDs soldados en la placa (no el header de 40 pines).

Por defecto están en modo "heartbeat" (parpadean solos según la carga del
sistema). Este script los pone en modo manual, los hace parpadear, y al
salir (Ctrl+C) los devuelve a "heartbeat".

Requiere haber corrido setup_gpio_permissions.sh una vez (grupo "gpio").
"""
import time

LEDS = ["green_led", "blue_led"]
BASE = "/sys/class/leds/{led}/{attr}"


def write(led, attr, value):
    with open(BASE.format(led=led, attr=attr), "w") as f:
        f.write(str(value))


def set_trigger(led, trigger):
    write(led, "trigger", trigger)


def set_brightness(led, on):
    write(led, "brightness", 1 if on else 0)


print("Tomando control manual de los LEDs...")
for led in LEDS:
    set_trigger(led, "none")

try:
    while True:
        for led in LEDS:
            print(f"{led}: ON")
            set_brightness(led, True)
            time.sleep(0.5)
            print(f"{led}: OFF")
            set_brightness(led, False)
except KeyboardInterrupt:
    print("\nDevolviendo control a heartbeat...")
    for led in LEDS:
        set_trigger(led, "heartbeat")
    print("Listo.")
