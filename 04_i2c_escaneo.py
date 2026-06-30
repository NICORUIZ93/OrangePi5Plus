"""
Módulo 4 — Enumeración de dispositivos en el bus I2C
=====================================================

Objetivo de aprendizaje
-----------------------
Comprender la estructura del protocolo I2C, el espacio de direcciones de
7 bits y el procedimiento de enumeración de dispositivos mediante el envío
de tramas de prueba, implementado con la biblioteca smbus2 de Python.

Marco teórico
-------------
I2C (Inter-Integrated Circuit) es un protocolo de comunicación serie
síncrono de dos hilos desarrollado por Philips Semiconductors en 1982.
Opera bajo un esquema maestro-esclavo con las siguientes características:

    SDA  (Serial Data Line)   — línea de datos bidireccional
    SCL  (Serial Clock Line)  — señal de reloj, siempre generada por el maestro

Ambas líneas son open-drain con resistencias de pull-up externas, lo que
permite que cualquier dispositivo pueda llevar la línea a estado bajo
sin conflictos de bus.

Velocidades estándar definidas por la especificación I2C:
    Modo estándar      100 kbit/s
    Modo rápido        400 kbit/s
    Modo rápido-plus   1 Mbit/s
    Modo de alta vel.  3.4 Mbit/s

Espacio de direcciones
----------------------
El protocolo define direcciones de 7 bits, lo que da 128 posibles valores
(0x00 – 0x7F). Sin embargo, los rangos 0x00–0x07 y 0x78–0x7F están
reservados por la especificación para funciones especiales (llamada
general, CBUS, protocolos alternativos). El rango disponible para
dispositivos de usuario es 0x08 – 0x77 (112 direcciones).

Proceso de enumeración
-----------------------
El procedimiento consiste en intentar iniciar una transacción de lectura
con cada dirección del rango disponible:

    1. El maestro envía la condición de START.
    2. El maestro transmite la dirección de 7 bits seguida del bit R/W = 1.
    3. Si un dispositivo ocupa esa dirección, responde con un bit ACK.
    4. El maestro envía STOP sin leer datos.

Si no hay ACK (condición NACK), el sistema operativo eleva la excepción
OSError con errno EREMOTEIO. El escaneo registra las direcciones que
responden.

El bus I2C-2 está disponible en el cabecero de 40 pines mediante el
overlay i2c2-m0:

    Pin físico 3  →  SDA (I2C-2)
    Pin físico 5  →  SCL (I2C-2)

Prerrequisitos del sistema
--------------------------
    Haber ejecutado setup_gpio_permissions.sh y reiniciado el sistema.
    El usuario debe pertenecer al grupo 'i2c'.
    Instalar smbus2: pip3 install smbus2

Uso
---
    python3 04_i2c_escaneo.py [número_de_bus]
    Ejemplo: python3 04_i2c_escaneo.py 7
"""

import sys

import smbus2

RANGO_INICIO = 0x03
RANGO_FIN    = 0x78

bus_num = int(sys.argv[1]) if len(sys.argv) > 1 else 2

print(f"Escaneando I2C-{bus_num}  (rango 0x{RANGO_INICIO:02X} – 0x{RANGO_FIN - 1:02X})")
print("-" * 50)

bus = smbus2.SMBus(bus_num)
encontrados = []

for direccion in range(RANGO_INICIO, RANGO_FIN):
    try:
        bus.read_byte(direccion)
        encontrados.append(direccion)
    except OSError:
        pass   # NACK: no hay dispositivo en esta dirección

bus.close()

if encontrados:
    print(f"Dispositivos detectados: {len(encontrados)}")
    for addr in encontrados:
        print(f"    0x{addr:02X}  (decimal {addr:3d})")
else:
    print("No se detectó ningún dispositivo.")
    print("Verifique las conexiones físicas y las resistencias de pull-up.")
