"""
Módulo 6 — Verificación del bus SPI mediante prueba de loopback
===============================================================

Objetivo de aprendizaje
-----------------------
Comprender el protocolo SPI, su naturaleza full-duplex y su gestión desde
Python mediante spidev, con énfasis en un comportamiento no documentado
de la API que puede conducir a errores de validación silenciosos.

Marco teórico
-------------
SPI (Serial Peripheral Interface) es un protocolo de comunicación serie
síncrono full-duplex desarrollado por Motorola (1979). Utiliza cuatro
señales:

    MOSI  (Master Out Slave In)   — datos del maestro al esclavo
    MISO  (Master In Slave Out)   — datos del esclavo al maestro
    SCLK  (Serial Clock)          — reloj, siempre generado por el maestro
    CS    (Chip Select, activo en bajo) — selección del esclavo destino

En cada ciclo de reloj, el maestro desplaza un bit por MOSI y recibe
simultáneamente un bit por MISO. Esto significa que transmisión y
recepción ocurren en paralelo en el mismo ciclo, de ahí el término
full-duplex.

Modos de operación (CPOL/CPHA)
--------------------------------
SPI define cuatro modos según la polaridad del reloj en reposo (CPOL)
y la fase de muestreo (CPHA):

    Modo 0  CPOL=0, CPHA=0  — reloj en bajo en reposo, muestreo en flanco de subida
    Modo 1  CPOL=0, CPHA=1
    Modo 2  CPOL=1, CPHA=0
    Modo 3  CPOL=1, CPHA=1  — reloj en alto en reposo, muestreo en flanco de bajada

El modo 0 es el más común y el que usan la mayoría de sensores y memorias.

Prueba de loopback
------------------
Cortocircuitar MOSI con MISO hace que cada byte enviado regrese
inmediatamente al maestro, sin necesidad de un esclavo externo. Permite
verificar la integridad eléctrica del bus y el correcto funcionamiento
del driver del kernel.

Comportamiento de spidev.xfer2()
----------------------------------
La función xfer2(lista) de la biblioteca spidev modifica la lista pasada
como argumento in-place y retorna la misma referencia de objeto (no crea
una copia). Consecuencia: tras la llamada, el argumento original apunta a
los datos RECIBIDOS, no a los enviados.

    enviado  = [0xAA, 0x55]
    recibido = spi.xfer2(enviado)    # INCORRECTO
    # En este punto, enviado y recibido son el mismo objeto.
    # La comparación enviado == recibido es trivialmente True.

    recibido = spi.xfer2(list(enviado))  # CORRECTO: se pasa una copia

Pines del bus SPI-0 en el cabecero de 40 pines
-----------------------------------------------
    Pin físico 19  →  MOSI
    Pin físico 21  →  MISO  (conectar a MOSI con un puente para el loopback)
    Pin físico 23  →  SCLK
    Pin físico 24  →  CS0   (/dev/spidev0.0)
    Pin físico 26  →  CS1   (/dev/spidev0.1)

Prerrequisitos del sistema
--------------------------
    Haber ejecutado setup_gpio_permissions.sh y reiniciado el sistema.
    El overlay spi0-m2-cs0-cs1-spidev debe estar activo.
    El usuario debe pertenecer al grupo 'spi'.

Uso
---
    python3 06_spi_loopback.py
    Para el loopback completo: puentear pin 19 (MOSI) con pin 21 (MISO).
"""

import spidev

VELOCIDAD_HZ = 500_000   # 500 kHz

spi = spidev.SpiDev()
spi.open(0, 0)             # bus 0, chip-select 0 → /dev/spidev0.0
spi.max_speed_hz = VELOCIDAD_HZ
spi.mode = 0               # CPOL=0, CPHA=0

trama_original = [0x00, 0x01, 0x55, 0xAA, 0xFF]

print(f"Bus SPI-0 inicializado.  Velocidad: {VELOCIDAD_HZ // 1000} kHz  Modo: {spi.mode}")
print(f"Trama enviada  : {[hex(b) for b in trama_original]}")

# Se pasa una copia para preservar trama_original sin modificar
trama_recibida = spi.xfer2(list(trama_original))

print(f"Trama recibida : {[hex(b) for b in trama_recibida]}")
print()

if trama_recibida == trama_original:
    print("Resultado: LOOPBACK VERIFICADO")
    print("La trama retornó íntegra. Bus SPI operativo con puente MOSI-MISO.")
else:
    print("Resultado: tramas distintas.")
    print("Esperado si no existe puente MOSI-MISO ni esclavo conectado.")
    print("El bus transmitió sin error de E/S.")

spi.close()
