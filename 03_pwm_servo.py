"""
Módulo 3 — Control de posición angular mediante PWM por hardware
================================================================

Objetivo de aprendizaje
-----------------------
Comprender el principio de modulación por ancho de pulso (PWM), su
generación mediante periférico dedicado del SoC y su aplicación en el
control de servomotores de radio control mediante la interfaz sysfs del
kernel Linux.

Marco teórico
-------------
La modulación por ancho de pulso (Pulse Width Modulation, PWM) genera
una señal digital periódica definida por dos parámetros:

    T           — período de la señal (inverso de la frecuencia)
    t_alto      — duración del pulso en estado alto

    duty_cycle [%] = (t_alto / T) × 100

Los servomotores estándar de radio control (tipo SG90, MG996R, etc.)
interpretan una señal PWM de 50 Hz (T = 20 ms) y traducen el ancho del
pulso en una posición angular:

    t_alto = 0.5 ms  → posición mínima  (≈   0°)
    t_alto = 1.5 ms  → posición central (≈  90°)
    t_alto = 2.5 ms  → posición máxima  (≈ 180°)

Si se generara esta señal desde Python con time.sleep(), la latencia del
planificador del SO introduciría variaciones (jitter) de ±1–5 ms, lo que
haría temblar el servo. El periférico PWM por hardware genera la señal
de manera autónoma, con jitter de nanosegundos, sin ocupar la CPU.

Interfaz sysfs del subsistema PWM
----------------------------------
El kernel Linux expone los controladores PWM como un árbol de archivos
virtuales en /sys/class/pwm/:

    /sys/class/pwm/pwmchipN/
        npwm              → número de canales disponibles
        export            → escribir "0" crea el subdirectorio pwm0
        pwm0/
            period        → período total en nanosegundos
            duty_cycle    → tiempo en alto en nanosegundos
            enable        → "1" activa la señal, "0" la desactiva

Todos los valores se expresan en nanosegundos para máxima resolución.

PWM14 en la Orange Pi 5 Plus
----------------------------
El servo usa el pin físico 7 del cabecero de 40 pines. En esta imagen
ese pin corresponde al overlay pwm14-m0 y al controlador:

    /sys/class/pwm/pwmchip2/pwm0

setup_gpio_permissions.sh configura el overlay, exporta el canal y asigna
permisos al grupo gpio en cada arranque.

Conexiones de hardware
-----------------------
    Pin físico 2  → cable rojo   del servo (VCC 5 V)
    Pin físico 6  → cable negro  del servo (GND)
    Pin físico 7  → cable de señal del servo (PWM14)

Prerrequisitos del sistema
--------------------------
    Haber ejecutado setup_gpio_permissions.sh y reiniciado el sistema.
    El overlay pwm14-m0 debe estar activo en /boot/orangepiEnv.txt.

Uso
---
    python3 03_pwm_servo.py
"""

import os
import time

CHIP_PWM   = "/sys/class/pwm/pwmchip2"
CANAL_PWM  = f"{CHIP_PWM}/pwm0"
PERIODO_NS = 20_000_000   # 20 ms → 50 Hz

PULSO_MIN  = 500    # µs
PULSO_CTR  = 1500   # µs
PULSO_MAX  = 2500   # µs


def escribir_sysfs(ruta: str, valor) -> None:
    with open(ruta, "w") as archivo:
        archivo.write(str(valor))


def leer_sysfs(ruta: str) -> str:
    with open(ruta, "r") as archivo:
        return archivo.read().strip()


def exportar_canal() -> None:
    """Solicita al kernel que instancie el canal pwm0 si no existe aún."""
    if not os.path.isdir(CANAL_PWM):
        escribir_sysfs(f"{CHIP_PWM}/export", 0)
        time.sleep(0.2)


def establecer_posicion(microsegundos: int) -> None:
    if not (PULSO_MIN <= microsegundos <= PULSO_MAX):
        raise ValueError(
            f"Ancho de pulso {microsegundos} µs fuera del rango "
            f"[{PULSO_MIN}, {PULSO_MAX}] µs."
        )
    escribir_sysfs(f"{CANAL_PWM}/duty_cycle", microsegundos * 1000)


exportar_canal()
if leer_sysfs(f"{CANAL_PWM}/enable") == "1":
    escribir_sysfs(f"{CANAL_PWM}/enable", 0)
escribir_sysfs(f"{CANAL_PWM}/duty_cycle", 0)
escribir_sysfs(f"{CANAL_PWM}/period", PERIODO_NS)
establecer_posicion(PULSO_CTR)
escribir_sysfs(f"{CANAL_PWM}/enable", 1)

print("Servomotor inicializado.")
print(f"  Período : {PERIODO_NS / 1e6:.0f} ms  ({1e9 / PERIODO_NS:.0f} Hz)")
print(f"  Rango   : {PULSO_MIN} µs – {PULSO_MAX} µs  (centro: {PULSO_CTR} µs)")
print()

try:
    while True:
        try:
            entrada = input(f"Ancho de pulso en µs [{PULSO_MIN}–{PULSO_MAX}]: ")
        except EOFError:
            break

        try:
            pulso = int(entrada)
            establecer_posicion(pulso)
            duty = pulso * 1000 / PERIODO_NS * 100
            print(f"  → duty cycle: {duty:.2f}%  ({pulso} µs / {PERIODO_NS / 1e6:.0f} ms)")
        except ValueError as error:
            print(f"  Error: {error}")

except KeyboardInterrupt:
    pass
finally:
    escribir_sysfs(f"{CANAL_PWM}/enable", 0)
    print("\nPWM desactivado.")
