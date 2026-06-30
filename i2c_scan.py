"""Escanea un bus I2C y lista las direcciones que responden.

Requiere haber corrido setup_gpio_permissions.sh una vez (grupo "i2c").
Uso: python3 i2c_scan.py [numero_de_bus]   (por defecto bus 2)
"""
import sys

import smbus2

bus_num = int(sys.argv[1]) if len(sys.argv) > 1 else 2

print(f"Escaneando i2c-{bus_num}...")
bus = smbus2.SMBus(bus_num)

encontrados = []
for addr in range(0x03, 0x78):
    try:
        bus.read_byte(addr)
        encontrados.append(addr)
    except OSError:
        pass

bus.close()

if encontrados:
    print("Dispositivos encontrados:")
    for addr in encontrados:
        print(f"  0x{addr:02X}")
else:
    print("Ningún dispositivo respondió (bus vacío o nada conectado).")
