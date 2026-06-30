"""
Módulo 2 — Lectura de entrada digital con detección de flancos por hardware
============================================================================

Objetivo de aprendizaje
-----------------------
Configurar una línea GPIO como entrada con resistencia de pull-up interna
y capturar eventos de flanco mediante la interfaz bloqueante de libgpiod v2,
evitando el consumo de CPU asociado al polling activo.

Marco teórico
-------------
Existen dos estrategias fundamentales para detectar cambios en una señal
digital desde software:

    Polling activo
        El proceso consulta el nivel de la línea repetidamente en cada
        iteración de un bucle. Consume tiempo de CPU de manera continua,
        incluso en ausencia de eventos.

    Notificación por flanco (edge-triggered interrupt)
        El hardware genera una interrupción al detectar una transición de
        señal. El kernel encola el evento y el proceso lo lee mediante una
        llamada bloqueante (equivalente a read() sobre el file descriptor).
        El procesador queda disponible para otras tareas mientras espera.

libgpiod v2 implementa la segunda estrategia. El método
request.read_edge_events() bloquea la ejecución hasta recibir un evento,
momento en que retorna un objeto EdgeEvent con tipo de flanco y marca de
tiempo en nanosegundos desde el inicio del sistema (CLOCK_MONOTONIC).

Rebote mecánico (bouncing)
--------------------------
Los pulsadores mecánicos presentan oscilaciones eléctricas (rebote) de
duración variable, típicamente entre 1 y 20 ms. Durante este tiempo, una
sola pulsación física genera múltiples transiciones. libgpiod v2 incorpora
filtrado de rebote en hardware (vía kernel) mediante el parámetro
debounce_period, que descarta transiciones más cortas que el período
especificado.

Resistencias de pull-up y pull-down
-------------------------------------
Cuando un pulsador no está presionado, la línea GPIO queda eléctricamente
en estado indefinido (floating) sin una referencia de tensión. Las
resistencias de pull-up conectan la línea a VCC (línea en ALTO en reposo),
mientras que las de pull-down la conectan a GND (línea en BAJO en reposo).
El RK3588 incorpora resistencias configurables por software en cada línea.

Conexiones de hardware
-----------------------
    Pin físico 13 (GPIO3_A4) ─── terminal A del pulsador
    Pin físico 14 (GND)      ─── terminal B del pulsador

    Con pull-up interno activo:
        Reposo (pulsador abierto)   → línea en ALTO (3.3 V)
        Presionado (circuito cerrado) → línea en BAJO (0 V)

Prerrequisitos del sistema
--------------------------
    Haber ejecutado setup_gpio_permissions.sh y reiniciado el sistema.
    El usuario debe pertenecer al grupo 'gpio'.

Uso
---
    python3 02_gpio_entrada.py
"""

import datetime

import gpiod
from gpiod.line import Bias, Direction, Edge

CHIP      = "/dev/gpiochip3"
LINEA     = 4   # GPIO3_A4, pin físico 13

configuracion = gpiod.LineSettings(
    direction=Direction.INPUT,
    bias=Bias.PULL_UP,
    edge_detection=Edge.BOTH,
    debounce_period=datetime.timedelta(milliseconds=5),
)

with gpiod.request_lines(
    CHIP,
    consumer="gpio-entrada-flancos",
    config={LINEA: configuracion},
) as solicitud:

    print("Línea GPIO3_A4 configurada: INPUT, PULL_UP, detección de flancos.")
    print("Esperando eventos (Ctrl+C para salir)...\n")

    try:
        for evento in solicitud.read_edge_events():
            ts_s = evento.timestamp_ns / 1e9

            if evento.event_type == gpiod.EdgeEvent.Type.FALLING_EDGE:
                print(f"  [{ts_s:12.6f} s]  Flanco de BAJADA  → pulsador presionado")
            else:
                print(f"  [{ts_s:12.6f} s]  Flanco de SUBIDA  → pulsador soltado")

    except KeyboardInterrupt:
        print("\nDetección de flancos finalizada.")
