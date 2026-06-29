import wiringpi
from wiringpi import GPIO

print("Iniciando configuración PWM...")
pwm_pin = 2  # wPi pin 2 (verificar en tabla)
wiringpi.wiringPiSetup()
print("Configuración finalizada.")

wiringpi.pinMode(pwm_pin, GPIO.PWM_OUTPUT)
print("Pin configurado como salida PWM.")

wiringpi.pwmSetMode(pwm_pin, GPIO.PWM_MODE_MS)
print("Modo PWM configurado.")

wiringpi.pwmSetClock(pwm_pin, 472)
print("Reloj PWM configurado.")

wiringpi.pwmSetRange(pwm_pin, 1024)
print("Rango PWM configurado.")

try:
    while True:
        duty = int(input("Ingrese valor PWM (0-1024): "))
        print(f"Estableciendo valor PWM: {duty}")
        wiringpi.pwmWrite(pwm_pin, duty)
except KeyboardInterrupt:
    print("\nControl PWM detenido. Apagando...")
    wiringpi.pwmWrite(pwm_pin, 0)  # Apagar al salir
    print("Programa finalizado.")
