import time

# PWM14 (físico pin 7, wPi 2), expuesto como canal 0 de pwmchip2 con el
# overlay "pwm14-m0". El servicio systemd pwm-setup.service se encarga de
# exportarlo y darle permisos de grupo "gpio" en cada arranque.
PWM_CHIP = "/sys/class/pwm/pwmchip2"
PWM_CHANNEL = f"{PWM_CHIP}/pwm0"
PERIOD_NS = 20_000_000  # 20ms = 50Hz, estándar para servos


def write(path, value):
    with open(path, "w") as f:
        f.write(str(value))


def ensure_exported():
    if not __import__("os").path.isdir(PWM_CHANNEL):
        write(f"{PWM_CHIP}/export", 0)
        time.sleep(0.2)


print("Iniciando configuración PWM...")
ensure_exported()
write(f"{PWM_CHANNEL}/period", PERIOD_NS)
write(f"{PWM_CHANNEL}/enable", 1)
print("PWM configurado y habilitado (50Hz).")

try:
    while True:
        us = int(input("Ingrese ancho de pulso en microsegundos (500-2500, centro=1500): "))
        print(f"Estableciendo duty_cycle: {us}us")
        write(f"{PWM_CHANNEL}/duty_cycle", us * 1000)
except KeyboardInterrupt:
    print("\nControl PWM detenido. Apagando...")
    write(f"{PWM_CHANNEL}/enable", 0)
    print("Programa finalizado.")
