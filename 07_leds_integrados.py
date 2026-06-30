"""
Módulo 7 — Control de LEDs integrados mediante el subsistema leds del kernel
=============================================================================

Objetivo de aprendizaje
-----------------------
Comprender el subsistema LED de Linux, el concepto de triggers como
mecanismo de control autónomo del kernel, y cómo transferir o ceder el
control de los LEDs integrados desde una aplicación de espacio de usuario.

Marco teórico
-------------
El subsistema LED de Linux (drivers/leds/) gestiona dispositivos
emisores de luz mediante una abstracción uniforme expuesta en sysfs:

    /sys/class/leds/<nombre>/
        brightness    — nivel de brillo (0 = apagado, valor > 0 = encendido)
        max_brightness — valor máximo soportado
        trigger       — modo de control activo (ver más abajo)

Triggers
--------
Un trigger es un módulo del kernel que controla el LED de forma autónoma
según algún criterio del sistema. El archivo trigger contiene la lista de
triggers disponibles; el activo aparece entre corchetes:

    $ cat /sys/class/leds/green_led/trigger
    none rc-feedback ... [heartbeat] timer ...

Triggers más relevantes:

    none        Control totalmente manual desde espacio de usuario.
    heartbeat   Parpadeo cuya frecuencia es función de la carga del sistema.
                Implementa el patrón cardíaco: dos pulsos rápidos con pausa.
    timer       Parpadeo a frecuencia fija. Configurable mediante delay_on
                y delay_off (en ms) bajo el directorio del LED.
    phy0tx      Actividad de transmisión en la interfaz WiFi.
    mmc0        Actividad de lectura/escritura en la tarjeta SD.

Adquisición de control
----------------------
Para controlar un LED manualmente, es necesario escribir "none" en el
archivo trigger. Esto desregistra el trigger activo y cede el control
al proceso actual. Escribir el nombre de un trigger lo reactiva.

La Orange Pi 5 Plus incorpora dos LEDs soldados en la placa:
    green_led  — LED verde
    blue_led   — LED azul

Prerrequisitos del sistema
--------------------------
    Haber ejecutado setup_gpio_permissions.sh y reiniciado el sistema.
    El usuario debe pertenecer al grupo 'gpio'.

Uso
---
    python3 07_leds_integrados.py
"""

import time

LEDS  = ["green_led", "blue_led"]
SYSFS = "/sys/class/leds/{led}/{attr}"


def escribir(led: str, attr: str, valor) -> None:
    with open(SYSFS.format(led=led, attr=attr), "w") as f:
        f.write(str(valor))


def leer_trigger_activo(led: str) -> str:
    with open(SYSFS.format(led=led, attr="trigger")) as f:
        contenido = f.read()
    for token in contenido.split():
        if token.startswith("[") and token.endswith("]"):
            return token[1:-1]
    return "desconocido"


print("Adquiriendo control manual de los LEDs integrados...")
for led in LEDS:
    trigger_previo = leer_trigger_activo(led)
    escribir(led, "trigger", "none")
    print(f"  {led}: '{trigger_previo}' → 'none' (control manual)")

print("\nControl adquirido. Iniciando secuencia (Ctrl+C para salir).\n")

try:
    while True:
        for led in LEDS:
            print(f"  {led}: ENCENDIDO")
            escribir(led, "brightness", 1)
            time.sleep(0.4)
            print(f"  {led}: APAGADO")
            escribir(led, "brightness", 0)
            time.sleep(0.1)

except KeyboardInterrupt:
    print("\nRestaurando trigger 'heartbeat'...")
    for led in LEDS:
        escribir(led, "trigger", "heartbeat")
        print(f"  {led}: restaurado")
    print("Finalizado.")
