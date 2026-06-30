"""
Módulo 1 — Control de salida digital mediante GPIO
===================================================

Objetivo de aprendizaje
-----------------------
Comprender la arquitectura del subsistema GPIO del SoC RK3588 y su
representación en Linux como character device, y controlar una línea
de salida digital desde Python utilizando la biblioteca libgpiod v2.

Marco teórico
-------------
El RK3588 organiza sus pines de E/S de propósito general en bancos
numerados del 0 al 5. Cada banco contiene hasta 32 líneas agrupadas
en cuatro puertos de ocho bits, designados con las letras A, B, C y D.

La numeración global (global line offset) de cualquier línea se obtiene
mediante la fórmula:

    número_global = banco × 32 + (letra − A) × 8 + bit

    Ejemplo: GPIO3_A1  →  3 × 32 + 0 × 8 + 1 = 97

El kernel Linux expone cada banco a través del subsistema GPIO Character
Device como el archivo de dispositivo /dev/gpiochipN, donde N coincide
con el número de banco. Las operaciones sobre estas líneas se realizan
mediante llamadas ioctl() al descriptor de archivo correspondiente.

La biblioteca libgpiod encapsula dichas llamadas y proporciona una API de
alto nivel sin necesidad de privilegios root, a diferencia de las
bibliotecas legacy (wiringpi, RPi.GPIO) que acceden directamente a
/dev/mem y requieren permisos de superusuario.

El acceso por grupo es posible porque /dev/gpiochipN otorga control solo
sobre las líneas de ese banco, no sobre el espacio de memoria completo.

Conexiones de hardware
-----------------------
    Pin físico 12  ─── 330 Ω ─── LED ─── GND (pin físico 6)
                   GPIO3_A1

    La resistencia de 330 Ω limita la corriente a ≈ 10 mA con 3.3 V de
    salida del SoC, valor seguro para los GPIO del RK3588 (máx. 12 mA).

Prerrequisitos del sistema
--------------------------
    Haber ejecutado setup_gpio_permissions.sh y reiniciado el sistema.
    El usuario debe pertenecer al grupo 'gpio'.

Uso
---
    python3 01_gpio_salida.py
"""

import time

import gpiod
from gpiod.line import Direction, Value

CHIP  = "/dev/gpiochip3"   # banco GPIO3
LINEA = 1                   # GPIO3_A1: offset 1 dentro del banco 3

with gpiod.request_lines(
    CHIP,
    consumer="gpio-salida",
    config={LINEA: gpiod.LineSettings(direction=Direction.OUTPUT)},
) as solicitud:

    print("Línea GPIO3_A1 adquirida en modo salida.")
    print("Presione Ctrl+C para terminar.\n")

    try:
        ciclo = 0
        while True:
            ciclo += 1
            print(f"Ciclo {ciclo:04d} — ALTO  (3.3 V)")
            solicitud.set_value(LINEA, Value.ACTIVE)
            time.sleep(1.0)

            print(f"Ciclo {ciclo:04d} — BAJO  (0 V)")
            solicitud.set_value(LINEA, Value.INACTIVE)
            time.sleep(1.0)

    except KeyboardInterrupt:
        solicitud.set_value(LINEA, Value.INACTIVE)
        print("\nLínea llevada a estado bajo. GPIO liberado.")
