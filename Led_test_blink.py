import time

import gpiod
from gpiod.line import Direction, Value

# Pin físico 12 del header de 40 pines (GPIO3_A1, wPi 6 en la numeración wiringOP)
CHIP = "/dev/gpiochip3"
LINE = 1

print("Iniciando configuración...")
print(f"Pin del LED configurado: {CHIP} línea {LINE}")

with gpiod.request_lines(
    CHIP,
    consumer="led-blink",
    config={LINE: gpiod.LineSettings(direction=Direction.OUTPUT)},
) as request:
    print("Pin configurado como salida. Parpadeando (Ctrl+C para salir)...")
    try:
        while True:
            print("Encendiendo LED...")
            request.set_value(LINE, Value.ACTIVE)
            time.sleep(1)
            print("Apagando LED...")
            request.set_value(LINE, Value.INACTIVE)
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("\nParpadeo detenido. Apagando LED...")
        request.set_value(LINE, Value.INACTIVE)
        print("Programa finalizado.")
