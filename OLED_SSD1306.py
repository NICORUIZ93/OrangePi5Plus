import sys
import time
import math

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

# Configuración
I2C_ADDR = 0x3C  # Dirección I2C de la pantalla
PORT = 2         # Puerto I2C
WIDTH = 128      # Ancho de la pantalla
HEIGHT = 64      # Alto de la pantalla
SCALE = 20       # Escala de la onda sinusoidal
SPEED = 5      # Velocidad de movimiento de la onda
OFFSET_Y = HEIGHT // 2  # Desplazamiento vertical para centrar la onda
SCALE_INTERVAL = 10  # Intervalo para las marcas de escala en el eje Y
PHASE_INTERVAL = 20  # Intervalo para las marcas de escala en el eje X

# Inicialización del dispositivo
serial = i2c(port=PORT, address=I2C_ADDR)
device = ssd1306(serial, width=WIDTH, height=HEIGHT)

# Cargar una fuente
# Reemplaza con la ruta real si es diferente
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
try:
    font = ImageFont.truetype(font_path, 8)  # Tamaño de la fuente
except IOError:
    print(
        f"No se pudo cargar la fuente {font_path}. Usando una fuente predeterminada.")
    font = ImageFont.load_default()


def draw_sine_wave(phase):
    """Dibuja una onda sinusoidal en la pantalla con escalas."""
    with canvas(device) as draw:
        # Limpia la pantalla
        draw.rectangle(device.bounding_box, fill="black")

        # Dibuja la onda sinusoidal
        for x in range(WIDTH):
            y = int(OFFSET_Y + SCALE *
                    math.sin((x + phase) * 2 * math.pi / WIDTH))
            if 0 <= y < HEIGHT:
                draw.point((x, y), fill="white")

        # Dibuja las marcas de escala en el eje Y
        for y_val in range(0, HEIGHT, SCALE_INTERVAL):
            draw.line((0, y_val, 5, y_val), fill="white")
            draw.text((7, y_val - 5), str(y_val - OFFSET_Y),
                      fill="white", font=font)  # Muestra el valor de y

        # Dibuja las marcas de escala en el eje X (solo marcas)
        for x in range(0, WIDTH, PHASE_INTERVAL):
            draw.line((x, HEIGHT - 5, x, HEIGHT), fill="white")

        # Etiquetas de los ejes
        draw.text((WIDTH - 20, HEIGHT - 10), "X", fill="white", font=font)
        draw.text((2, 0), "Y", fill="white", font=font)


def main():
    """Función principal del programa."""
    print("Iniciando programa...")
    phase = 0  # Fase inicial de la onda

    try:
        while True:
            draw_sine_wave(phase)
            phase += SPEED  # Incrementa la fase para el movimiento
            time.sleep(0.01)  # Pequeña pausa para controlar la velocidad
    except KeyboardInterrupt:
        print("\nSaliendo...")
        sys.exit(0)


if __name__ == '__main__':
    main()
