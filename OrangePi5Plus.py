import wiringpi

# Configuración inicial
print("Iniciando configuración...")
wiringpi.wiringPiSetup()  # Usa numeración secuencial (wPi)
print("Configuración finalizada.")

led_pin = 6  # Verifica el número wPi con 'gpio readall'
print(f"Pin del LED configurado: {led_pin}")

wiringpi.pinMode(led_pin, 1)  # 1 = OUTPUT
print("Pin configurado como salida.")

# Parpadeo
try:
    while True:
        print("Encendiendo LED...")
        wiringpi.digitalWrite(led_pin, 1)  # HIGH
        wiringpi.delay(1000)  # Espera 0.5 segundos
        print("Apagando LED...")
        wiringpi.digitalWrite(led_pin, 0)  # LOW
        wiringpi.delay(1500)  # Espera 0.5 segundos


except KeyboardInterrupt:
    print("\nParpadeo detenido. Apagando LED...")
    wiringpi.digitalWrite(led_pin, 0)  # Apagar al salir
    print("Programa finalizado.")
