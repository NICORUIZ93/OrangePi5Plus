"""Prueba de bus SPI0 enviando y leyendo bytes.

Para verificar que el bus funciona de punta a punta sin ningún periférico
SPI real, puentea con un cable MOSI (pin físico 19) con MISO (pin físico
21) y los bytes que se envían deberían volver idénticos ("loopback").

Sin el puente, esto igual confirma que el bus abre y transmite sin error
(I/O), pero los bytes leídos no van a coincidir con los enviados.

Requiere haber corrido setup_gpio_permissions.sh una vez (grupo "spi") y
tener el overlay spi0-m2-cs0-cs1-spidev activo (lo activa el mismo script).
"""
import spidev

spi = spidev.SpiDev()
spi.open(0, 0)  # bus 0, chip-select 0 (pin físico 24)
spi.max_speed_hz = 500_000

enviado = [0x01, 0x02, 0x03, 0xAA, 0xFF]
print(f"Enviando: {enviado}")
# xfer2 modifica la lista en el lugar y devuelve la misma referencia,
# por eso se manda una copia: si no, "enviado" cambiaría también.
recibido = spi.xfer2(list(enviado))
print(f"Recibido: {recibido}")

if recibido == enviado:
    print("Loopback OK: los bytes volvieron idénticos (MOSI-MISO puenteados).")
else:
    print("Los bytes no coinciden — normal si no hay un puente MOSI-MISO ni "
          "ningún dispositivo SPI conectado. El bus en sí transmitió sin error.")

spi.close()
