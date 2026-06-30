"""
Módulo 5 — Interfaz con pantalla OLED SSD1306 mediante el bus I2C
==================================================================

Objetivo de aprendizaje
-----------------------
Controlar una pantalla OLED monofásica de 128×64 píxeles basada en el
controlador SSD1306 a través del bus I2C, comprendiendo las capas de
abstracción de software involucradas desde Python hasta el driver del
kernel.

Marco teórico
-------------
Tecnología OLED
    Los displays OLED (Organic Light-Emitting Diode) emiten luz propia a
    nivel de píxel, sin necesidad de retroiluminación. Esto permite un
    contraste teóricamente infinito y un consumo proporcional a los píxeles
    encendidos.

Controlador SSD1306
    El SSD1306 de Solomon Systech es un controlador de pantalla OLED
    monofásica (un bit por píxel) muy utilizado en módulos de 128×64 y
    128×32 píxeles. Se comunica mediante I2C (dirección 0x3C o 0x3D según
    el pin SA0) o SPI de 4 hilos.

    Su organización interna divide la pantalla en 8 páginas horizontales,
    cada una de 8 filas de píxeles (128 × 8 = 1024 bytes de GDDRAM).

Pila de software
    La biblioteca luma.oled abstrae completamente el protocolo de
    inicialización y transferencia del SSD1306. El flujo es:

        Código Python (Pillow)
            ↓  canvas() → imagen PIL en memoria
        luma.oled (ssd1306)
            ↓  convierte la imagen a mapa de bits del GDDRAM
        luma.core (i2c serial)
            ↓  escribe bloques mediante smbus2
        Kernel Linux (i2c-dev)
            ↓  llama al driver i2c-rk3x del RK3588
        Hardware SSD1306

    La clase canvas() actúa como gestor de contexto (with): abre el
    framebuffer, expone el objeto ImageDraw de Pillow para dibujar, y al
    salir del bloque transfiere el framebuffer completo al controlador.

Conexiones de hardware
-----------------------
    Pin físico 1   →  VCC del módulo OLED  (3.3 V)
    Pin físico 6   →  GND del módulo OLED
    Pin físico 3   →  SDA del módulo OLED  (I2C-2)
    Pin físico 5   →  SCL del módulo OLED  (I2C-2)

Prerrequisitos del sistema
--------------------------
    Haber ejecutado setup_gpio_permissions.sh y reiniciado el sistema.
    Instalar dependencias: pip3 install luma.oled

Uso
---
    python3 05_i2c_oled.py
"""

import math
import time

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

serial     = i2c(port=2, address=0x3C)
dispositivo = ssd1306(serial)

ANCHO  = dispositivo.width    # 128 píxeles
ALTO   = dispositivo.height   #  64 píxeles

print(f"Pantalla SSD1306 inicializada: {ANCHO} × {ALTO} px")
print("Presione Ctrl+C para salir.")

fase = 0.0

try:
    while True:
        with canvas(dispositivo) as dibujo:
            dibujo.text((0, 0),  "Orange Pi 5 Plus", fill="white")
            dibujo.text((0, 10), f"I2C Bus 2 — SSD1306", fill="white")

            # Onda senoidal animada en la mitad inferior de la pantalla
            amplitud = (ALTO - 24) // 2
            centro_y = 24 + amplitud
            for x in range(ANCHO):
                y = int(centro_y + amplitud * math.sin(
                    2 * math.pi * x / ANCHO + fase
                ))
                dibujo.point((x, y), fill="white")

        fase += 0.12
        time.sleep(0.03)

except KeyboardInterrupt:
    dispositivo.clear()
    print("\nPantalla apagada.")
