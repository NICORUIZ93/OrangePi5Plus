# Tutorial completo: Orange Pi 5 Plus (RK3588)

Guía práctica para sacar el máximo provecho a la placa. Cada sección explica el **por qué** detrás de los comandos, incluye código real probado en el hardware, e indica las limitaciones conocidas de la imagen oficial de Orange Pi.

> **Prerrequisito único:** ejecuta estos dos scripts de setup una vez (requieren `sudo`) y luego **reinicia**:
> ```bash
> ./setup_gpio_permissions.sh   # GPIO, I2C, SPI, PWM, LEDs sin sudo
> ./setup_npu.sh                # runtime del NPU (RKNN)
> sudo reboot
> ```
> A partir del reinicio, todos los ejemplos de esta guía corren **sin `sudo`**.

---

## Índice

1. [Hardware de la placa](#1-hardware-de-la-placa)
2. [GPIO digital — encender/apagar un LED](#2-gpio-digital--encenderApagar-un-led)
3. [PWM por hardware — controlar un servo](#3-pwm-por-hardware--controlar-un-servo)
4. [I2C — comunicación con sensores y pantallas](#4-i2c--comunicación-con-sensores-y-pantallas)
5. [SPI — bus de alta velocidad](#5-spi--bus-de-alta-velocidad)
6. [LEDs onboard — los LEDs soldados en la placa](#6-leds-onboard--los-leds-soldados-en-la-placa)
7. [NPU — inferencia de IA a 6 TOPS](#7-npu--inferencia-de-ia-a-6-tops)
8. [GPU — aceleración gráfica OpenGL](#8-gpu--aceleración-gráfica-opengl)
9. [Audio — reproducción y grabación](#9-audio--reproducción-y-grabación)
10. [Red — Ethernet y WiFi](#10-red--ethernet-y-wifi)
11. [USB — dispositivos externos](#11-usb--dispositivos-externos)
12. [Cámara](#12-cámara)
13. [Referencia rápida: cabecero de 40 pines](#13-referencia-rápida-cabecero-de-40-pines)

---

## 1. Hardware de la placa

| Componente | Detalle |
|---|---|
| SoC | Rockchip RK3588 |
| CPU | 4× Cortex-A76 @ 2.4GHz + 4× Cortex-A55 @ 1.8GHz |
| RAM | 4/8/16 GB LPDDR4X |
| GPU | Mali-G610 MP4 (driver Panfrost, OpenGL ES 3.1 / OpenGL 3.0) |
| NPU | 3× 2 TOPS = **6 TOPS** (Rockchip RKNPU) |
| Ethernet | 2× 2.5GbE (RTL8125BG) |
| WiFi | 802.11 b/g/n/ac (AP6275P) |
| USB | 2× USB 3.0 + 2× USB 2.0 + 1× USB Type-C (OTG) |
| Almacenamiento | MicroSD + eMMC + M.2 NVMe (PCIe 3.0) |
| Video | HDMI 2.1 + DisplayPort 1.4 (via USB-C) + MIPI DSI |
| Cámara | 2× MIPI CSI |
| GPIO | 40 pines (compatible con Raspberry Pi en pinout) |
| OS de prueba | Ubuntu 22.04.5 LTS, kernel 5.10.110-rockchip-rk3588 |

### Por qué el kernel importa

La imagen oficial de Orange Pi usa un kernel **BSP (Board Support Package)** de Rockchip, rama `5.10.x`. Es un kernel vendor parcheado, no el mainline de kernel.org. Esto significa:

- El soporte para RK3588 en mainline Linux aún está madurando (llega en 6.x, pero con menos features)
- Algunos periféricos (NPU, VPU/codec de video) solo funcionan con drivers vendor
- El NPU en particular requiere el módulo `rknpu` que solo existe en este kernel

---

## 2. GPIO digital — encender/apagar un LED

### Conceptos

El cabecero de 40 pines expone líneas GPIO agrupadas en **bancos** (GPIO0…GPIO5). Cada banco tiene 32 líneas organizadas como: A0–A7, B0–B7, C0–C7, D0–D7.

Para calcular el número global de una línea:

```
número_global = banco × 32 + letra × 8 + bit
```

Por ejemplo, `GPIO3_A1` = 3×32 + 0×8 + 1 = **97**.

En el sistema de archivos del kernel, cada banco aparece como un `gpiochipN`:
- `gpiochip0` → banco GPIO0
- `gpiochip3` → banco GPIO3 (el que usamos aquí)

### Por qué NO usar `wiringpi`

La biblioteca `wiringpi` que viene en la imagen accede a `/dev/mem` (memoria física cruda). Para abrirlo sin root necesitarías darle al grupo acceso a **toda la RAM del sistema**, lo que sería una brecha de seguridad enorme. La alternativa correcta es `libgpiod`, que da acceso solo a las líneas GPIO puntuales que el programa pide.

### Instalación

```bash
sudo apt install python3-libgpiod   # o: pip3 install gpiod
```

### Ejemplo: `Led_test_blink.py`

Conecta un LED (con su resistencia de 330Ω) entre el **pin físico 12** y GND (pin físico 6).

```python
import time
import gpiod
from gpiod.line import Direction, Value

CHIP = "/dev/gpiochip3"   # banco GPIO3
LINE = 1                   # GPIO3_A1, pin físico 12

with gpiod.request_lines(
    CHIP,
    consumer="led-blink",
    config={LINE: gpiod.LineSettings(direction=Direction.OUTPUT)},
) as request:
    try:
        while True:
            print("Encendiendo LED...")
            request.set_value(LINE, Value.ACTIVE)
            time.sleep(1)
            print("Apagando LED...")
            request.set_value(LINE, Value.INACTIVE)
            time.sleep(1.5)
    except KeyboardInterrupt:
        request.set_value(LINE, Value.INACTIVE)
```

**Ejecutar:**
```bash
python3 Led_test_blink.py
```

### Leer un botón (input)

```python
import gpiod
from gpiod.line import Direction, Edge, Value

CHIP = "/dev/gpiochip3"
LINE = 2  # GPIO3_A2, pin físico 13

with gpiod.request_lines(
    CHIP,
    consumer="boton",
    config={LINE: gpiod.LineSettings(direction=Direction.INPUT,
                                      edge_detection=Edge.BOTH)},
) as request:
    print("Esperando cambios en el botón (Ctrl+C para salir)...")
    for event in request.read_edge_events():
        if event.event_type == gpiod.EdgeEvent.Type.RISING_EDGE:
            print("Botón presionado")
        else:
            print("Botón soltado")
```

### Comandos útiles de línea de comandos

```bash
# Listar todos los chips y sus líneas
gpiodetect

# Ver estado de todas las líneas de un chip
gpioinfo /dev/gpiochip3

# Leer el valor de una línea (sin Python)
gpioget /dev/gpiochip3 1

# Poner una línea en alto (sin Python)
gpioset /dev/gpiochip3 1=1
```

---

## 3. PWM por hardware — controlar un servo

### Por qué PWM por hardware

Un servo de radio control necesita una señal PWM a exactamente 50Hz (período de 20ms). Si la generaras desde Python con `time.sleep()`, el sistema operativo multitarea haría los tiempos imprecisos y el servo temblará. El PWM por hardware lo genera un periférico dedicado del SoC, completamente independiente de la CPU.

### El problema con el overlay por defecto

La imagen oficial activa el overlay `pwm0-m0`, pero ese pin está compartido con un bus I2C interno que lo reclama primero. El resultado es un error I/O al escribir en `enable`. El overlay correcto para el **pin físico 7** (etiquetado "PWM14" en el cabecero) es **`pwm14-m0`**, que expone `/sys/class/pwm/pwmchip2`.

`setup_gpio_permissions.sh` ya corrige esto automáticamente.

### Mapa de conceptos: sysfs PWM

```
/sys/class/pwm/
└── pwmchip2/           ← el controlador hardware (pwm14-m0 en esta placa)
    ├── npwm            ← cuántos canales tiene (1 en este caso)
    ├── export          ← escribe "0" aquí para crear el canal pwm0
    └── pwm0/           ← aparece tras exportar
        ├── period      ← período total en nanosegundos (20000000 = 20ms = 50Hz)
        ├── duty_cycle  ← tiempo en alto en nanosegundos
        └── enable      ← escribe "1" para activar
```

Ancho de pulso para servo estándar:
- `500000 ns` (0.5ms) → posición mínima (~0°)
- `1500000 ns` (1.5ms) → posición central (~90°)
- `2500000 ns` (2.5ms) → posición máxima (~180°)

### Ejemplo: `servo_test.py`

Conecta el servo al **pin físico 7** (PWM), **pin físico 2** (5V), **pin físico 6** (GND).

```python
import time
import os

PWM_CHIP    = "/sys/class/pwm/pwmchip2"
PWM_CHANNEL = f"{PWM_CHIP}/pwm0"
PERIOD_NS   = 20_000_000  # 20ms → 50Hz


def write(path, value):
    with open(path, "w") as f:
        f.write(str(value))


def ensure_exported():
    if not os.path.isdir(PWM_CHANNEL):
        write(f"{PWM_CHIP}/export", 0)
        time.sleep(0.2)


ensure_exported()
write(f"{PWM_CHANNEL}/period", PERIOD_NS)
write(f"{PWM_CHANNEL}/enable", 1)

try:
    while True:
        us = int(input("Ancho de pulso en µs (500–2500, centro=1500): "))
        write(f"{PWM_CHANNEL}/duty_cycle", us * 1000)
except KeyboardInterrupt:
    write(f"{PWM_CHANNEL}/enable", 0)
```

**Ejecutar:**
```bash
python3 servo_test.py
```

---

## 4. I2C — comunicación con sensores y pantallas

### Qué es I2C

I2C es un bus de dos cables (SDA = datos, SCL = reloj) que permite conectar varios dispositivos a la misma línea usando **direcciones de 7 bits**. Ideal para sensores (temperatura, acelerómetro, giroscopio) y pantallas pequeñas (OLED SSD1306).

La placa expone múltiples buses I2C. El más accesible en el cabecero de 40 pines es el **bus 2** (overlay `i2c2-m0`):
- SDA → pin físico 3
- SCL → pin físico 5

### Escanear el bus: `i2c_scan.py`

```python
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
    print("Ningún dispositivo respondió.")
```

```bash
python3 i2c_scan.py          # escanea bus 2
python3 i2c_scan.py 7        # escanea bus 7
```

### Leer un sensor de temperatura (BMP280 / BME280)

```bash
pip3 install adafruit-circuitpython-bmp280
```

```python
import board
import busio
import adafruit_bmp280

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)

print(f"Temperatura: {sensor.temperature:.1f} °C")
print(f"Presión:     {sensor.pressure:.1f} hPa")
```

### Pantalla OLED SSD1306 (128×64): `OLED_SSD1306.py`

```bash
pip3 install luma.oled
```

El script `OLED_SSD1306.py` incluido dibuja una onda senoidal animada. Extracto de lo más relevante:

```python
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
import math, time

serial = i2c(port=2, address=0x3C)   # bus 2, dirección estándar del SSD1306
device = ssd1306(serial)

t = 0
while True:
    with canvas(device) as draw:
        for x in range(128):
            y = int(32 + 28 * math.sin((x + t) * 0.1))
            draw.point((x, y), fill="white")
    t += 3
    time.sleep(0.03)
```

---

## 5. SPI — bus de alta velocidad

### Qué es SPI

SPI usa 4 cables: MOSI (datos del maestro al esclavo), MISO (datos del esclavo al maestro), SCLK (reloj) y CS (chip select, uno por dispositivo). Es más rápido que I2C y más simple de implementar, pero necesita un cable más por dispositivo.

Overlay activo: `spi0-m2-cs0-cs1-spidev`. Crea:
- `/dev/spidev0.0` → CS0 (pin físico 24)
- `/dev/spidev0.1` → CS1 (pin físico 26)

Pines en el cabecero:
| Función | Pin físico |
|---|---|
| MOSI | 19 |
| MISO | 21 |
| SCLK | 23 |
| CS0  | 24 |
| CS1  | 26 |

### Prueba de loopback: `spi_loopback_test.py`

Para verificar el bus sin conectar nada, puentea con un cable **MOSI (19) ↔ MISO (21)**.

```python
import spidev

spi = spidev.SpiDev()
spi.open(0, 0)              # bus 0, chip-select 0
spi.max_speed_hz = 500_000

enviado = [0x01, 0x02, 0x03, 0xAA, 0xFF]
print(f"Enviando: {enviado}")

# IMPORTANTE: xfer2() modifica la lista de entrada en el lugar
# y devuelve la misma referencia. Hay que pasar una copia.
recibido = spi.xfer2(list(enviado))
print(f"Recibido: {recibido}")

if recibido == enviado:
    print("Loopback OK: bytes idénticos (MOSI-MISO puenteados).")
else:
    print("Bytes distintos — sin puente ni dispositivo conectado es lo esperado.")

spi.close()
```

### Leer un sensor de temperatura MAX31855 (termopar)

```bash
pip3 install adafruit-circuitpython-max31855
```

```python
import board
import digitalio
import adafruit_max31855

spi = board.SPI()
cs  = digitalio.DigitalInOut(board.CE0)   # usa /dev/spidev0.0
sensor = adafruit_max31855.MAX31855(spi, cs)

print(f"Temperatura: {sensor.temperature:.1f} °C")
```

---

## 6. LEDs onboard — los LEDs soldados en la placa

### Cuáles son

La placa tiene dos LEDs soldados directamente (sin cabecero):
- **green_led** — LED verde de estado
- **blue_led** — LED azul de estado

Por defecto corren en modo `heartbeat`: parpadean solos a una frecuencia que refleja la carga del sistema (más rápido = más carga). Son controlados por el kernel a través del subsistema `/sys/class/leds/`.

### Ejemplo: `leds_onboard.py`

```python
import time

LEDS = ["green_led", "blue_led"]
BASE = "/sys/class/leds/{led}/{attr}"


def write(led, attr, value):
    with open(BASE.format(led=led, attr=attr), "w") as f:
        f.write(str(value))


print("Tomando control manual de los LEDs...")
for led in LEDS:
    write(led, "trigger", "none")   # quita el modo heartbeat

try:
    while True:
        for led in LEDS:
            print(f"{led}: ON")
            write(led, "brightness", 1)
            time.sleep(0.5)
            print(f"{led}: OFF")
            write(led, "brightness", 0)
except KeyboardInterrupt:
    print("\nDevolviendo heartbeat...")
    for led in LEDS:
        write(led, "trigger", "heartbeat")
```

### Otros modos de trigger disponibles

```bash
cat /sys/class/leds/green_led/trigger
# muestra: none rc-feedback kbd-scrolllock ... heartbeat ...

# modo timer: parpadea a frecuencia fija
echo "timer" > /sys/class/leds/green_led/trigger
echo 200 > /sys/class/leds/green_led/delay_on   # ms encendido
echo 800 > /sys/class/leds/green_led/delay_off  # ms apagado

# vinculado a actividad de red
echo "phy0tx" > /sys/class/leds/green_led/trigger

# restaurar
echo "heartbeat" > /sys/class/leds/green_led/trigger
```

---

## 7. NPU — inferencia de IA a 6 TOPS

### Qué es el NPU

El RK3588 incluye una unidad de procesamiento neuronal (NPU) de 3 núcleos con un rendimiento total de **6 TOPS** (tera-operaciones por segundo). Está optimizado para inferencia de redes neuronales convolucionales (CNN) como los modelos de detección de objetos, clasificación de imágenes, y reconocimiento facial.

El stack de software se llama **RKNN**:
- `rknn-toolkit2` (PC, Python): convierte modelos de PyTorch/TensorFlow/ONNX al formato `.rknn`
- `rknn-toolkit-lite2` (placa, Python): carga modelos `.rknn` y corre inferencia
- `librknnrt.so`: runtime C de bajo nivel que usa el kernel `rknpu`

### Mensajes de error en `dmesg` — son inofensivos

Al arrancar verás mensajes como:
```
RKNPU: can't request region for resource
failed to initialize power model
```

Esto es un bug conocido del kernel vendor. **No impide que el NPU funcione.** La inferencia corre con normalidad.

### Setup

```bash
./setup_npu.sh
```

Descarga solo los archivos necesarios (~15MB) del repo oficial sin clonar los 3.8GB completos.

### Ejemplo: `npu_inference_example.py`

Clasifica una imagen usando ResNet-18 precompilado para RK3588. La primera vez descarga el modelo y la imagen de prueba automáticamente.

```python
import os
import urllib.request
import cv2
import numpy as np
from rknnlite.api import RKNNLite

REPO       = "https://raw.githubusercontent.com/airockchip/rknn-toolkit2/master/rknn-toolkit-lite2/examples/resnet18"
MODEL_PATH = "resnet18_for_rk3588.rknn"
IMAGE_PATH = "space_shuttle_224.jpg"


def download_if_missing(path, url):
    if not os.path.exists(path):
        print(f"Descargando {path}...")
        urllib.request.urlretrieve(url, path)


download_if_missing(MODEL_PATH, f"{REPO}/{MODEL_PATH}")
download_if_missing(IMAGE_PATH, f"{REPO}/{IMAGE_PATH}")

rknn = RKNNLite()
print("Cargando modelo...")
rknn.load_rknn(MODEL_PATH)

print("Inicializando NPU...")
if rknn.init_runtime() != 0:
    raise RuntimeError("El NPU no respondió")

img = cv2.imread(IMAGE_PATH)
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
img = np.expand_dims(img, axis=0)

print("Corriendo inferencia...")
outputs  = rknn.inference(inputs=[img])
clase    = int(np.argmax(outputs[0]))
score    = float(outputs[0][0][clase])

print(f"\nClase predicha: {clase}  (score: {score:.2f})")
print("812 = 'space shuttle' — resultado correcto.")
rknn.release()
```

```bash
python3 npu_inference_example.py
```

### Convertir tu propio modelo

En un PC con Python 3.8–3.10 (no en la placa):

```bash
pip install rknn-toolkit2   # solo disponible para x86_64
```

```python
from rknn.api import RKNN

rknn = RKNN()
rknn.config(target_platform='rk3588')
rknn.load_onnx(model='mi_modelo.onnx')
rknn.build(do_quantization=True, dataset='calibration_dataset.txt')
rknn.export_rknn('mi_modelo.rknn')
rknn.release()
```

Luego copia `mi_modelo.rknn` a la placa y úsalo con `RKNNLite` igual que el ejemplo.

### Modelos precompilados disponibles

El repo `airockchip/rknn-toolkit2` incluye modelos listos para RK3588:
- ResNet-18/50 (clasificación)
- YOLOv5 / YOLOv8 (detección de objetos)
- MobileNetV2
- DeepLabV3 (segmentación)

```bash
# Ver todos los ejemplos disponibles:
# https://github.com/airockchip/rknn-toolkit2/tree/master/rknn-toolkit-lite2/examples
```

---

## 8. GPU — aceleración gráfica OpenGL

### Qué hay disponible

| API | Estado |
|---|---|
| OpenGL ES 3.1 | Funcional (driver Panfrost, open source) |
| OpenGL 3.0 | Funcional (Mesa 22.x) |
| Vulkan | Parcial (PanVK, experimental en esta versión de Mesa) |
| OpenCL | No disponible con Panfrost |

### Verificar el driver

```bash
glxinfo | grep -E "OpenGL vendor|OpenGL renderer|OpenGL version"
# OpenGL vendor string: Mesa/X.org
# OpenGL renderer string: Mali-G610 (Panfrost)
# OpenGL version string: 3.0 Mesa 22.x.x
```

### Ejemplo: ventana OpenGL con Python

```bash
pip3 install PyOpenGL PyOpenGL_accelerate glfw
```

```python
import glfw
import OpenGL.GL as gl

def main():
    if not glfw.init():
        return

    window = glfw.create_window(800, 600, "OpenGL en Mali-G610", None, None)
    glfw.make_context_current(window)

    while not glfw.window_should_close(window):
        gl.glClearColor(0.1, 0.2, 0.4, 1.0)   # azul oscuro
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

main()
```

### Benchmark rápido

```bash
# Mide FPS en un benchmark de rasterización OpenGL ES
glmark2-es2
```

---

## 9. Audio — reproducción y grabación

### Hardware disponible

```bash
aplay -l          # lista tarjetas de audio de reproducción
arecord -l        # lista tarjetas de grabación
```

Salida típica: `card 0: rockchiphdmi0` (HDMI), `card 1: rockchipes8388` (jack 3.5mm).

### Reproducir un archivo

```bash
# Reproducir en el jack 3.5mm (placa 1)
aplay -D hw:1,0 archivo.wav

# Con pipewire/pulseaudio instalado (más sencillo)
paplay archivo.wav
```

### Grabar desde el micrófono

```bash
arecord -D hw:1,0 -f cd -d 5 grabacion.wav
# -f cd = 16-bit, 44100Hz, estéreo | -d 5 = 5 segundos
```

### Reproducir y grabar con Python

```bash
pip3 install sounddevice soundfile numpy
```

```python
import sounddevice as sd
import soundfile as sf
import numpy as np

# Grabar 3 segundos
fs = 44100
print("Grabando 3 segundos...")
datos = sd.rec(int(3 * fs), samplerate=fs, channels=1)
sd.wait()
sf.write("grabacion.wav", datos, fs)
print("Guardado en grabacion.wav")

# Reproducir
datos, fs = sf.read("grabacion.wav")
sd.play(datos, fs)
sd.wait()
```

---

## 10. Red — Ethernet y WiFi

### Ethernet 2.5GbE

La placa tiene dos puertos Ethernet de 2.5 Gigabit (RTL8125BG). Con un switch o router que soporte 2.5GbE, la velocidad real supera los 2Gbps.

```bash
# Ver estado de las interfaces
ip link show

# Velocidad negociada (requiere cable conectado)
ethtool eth0 | grep Speed

# Test de ancho de banda (necesita iperf3 en otro equipo)
iperf3 -c <ip_del_servidor>
```

### WiFi

```bash
# Escanear redes disponibles
nmcli dev wifi list

# Conectarse
nmcli dev wifi connect "NombreRed" password "contraseña"

# Estado de la conexión
nmcli connection show --active
```

### Servidor web simple (ejemplo de aplicación de red)

```bash
pip3 install flask
```

```python
from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route("/temperatura")
def temperatura():
    # Lee la temperatura del CPU
    result = subprocess.run(
        ["cat", "/sys/class/thermal/thermal_zone0/temp"],
        capture_output=True, text=True
    )
    temp_mc = int(result.stdout.strip())    # en milicélsius
    return jsonify({"cpu_temp_c": temp_mc / 1000})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

```bash
python3 app.py
# Visita: http://<ip_de_la_placa>:8080/temperatura
```

---

## 11. USB — dispositivos externos

### Puertos disponibles

| Puerto | Velocidad | Ubicación |
|---|---|---|
| USB 3.0 × 2 | 5 Gbps | Conector tipo A azul |
| USB 2.0 × 2 | 480 Mbps | Conector tipo A negro |
| USB-C (OTG) | USB 3.2 Gen1 | Conector frontal |

### Listar dispositivos conectados

```bash
lsusb            # lista todos los dispositivos USB
lsusb -t         # muestra la topología en árbol
```

### Almacenamiento USB (pendrive / disco)

```bash
# Ver discos conectados
lsblk

# Montar manualmente
sudo mount /dev/sda1 /mnt/usb

# O automáticamente si udisks2 está instalado
udisksctl mount -b /dev/sda1
```

### Comunicación serial con Arduino / microcontroladores

```bash
pip3 install pyserial
```

```python
import serial
import time

# Ajusta el puerto (/dev/ttyUSB0 o /dev/ttyACM0)
ser = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=1)
time.sleep(2)   # espera al reset del Arduino

ser.write(b"hola\n")
respuesta = ser.readline()
print(f"Arduino dijo: {respuesta.decode().strip()}")
ser.close()
```

---

## 12. Cámara

### Estado actual

La placa tiene dos conectores MIPI CSI. El soporte de cámara en la imagen oficial de Orange Pi requiere:
1. Un módulo de cámara compatible (OV13850, IMX415, etc.)
2. El overlay de Device Tree correspondiente activado en `/boot/orangepiEnv.txt`

Sin módulo físico conectado, los dispositivos `/dev/videoN` no aparecerán.

### Verificar si hay cámara detectada

```bash
ls /dev/video*                # lista dispositivos de video
v4l2-ctl --list-devices       # muestra cámaras con sus capacidades
```

### Capturar un frame (si hay cámara)

```bash
# Capturar una foto
v4l2-ctl --device=/dev/video0 --stream-mmap --stream-count=1 \
          --stream-to=foto.raw

# Con ffmpeg (más sencillo)
ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 foto.jpg
```

### Con Python y OpenCV

```python
import cv2

cam = cv2.VideoCapture(0)
ret, frame = cam.read()
if ret:
    cv2.imwrite("foto.jpg", frame)
    print("Foto guardada.")
cam.release()
```

---

## 13. Referencia rápida: cabecero de 40 pines

```
       3.3V (1) (2) 5V
  GPIO0_C1 (3) (4) 5V          [SDA I2C2]
  GPIO0_B6 (5) (6) GND         [SCL I2C2]
  GPIO0_C0 (7) (8) GPIO0_D1    [PWM14]   [TX UART2]
        GND (9)(10) GPIO0_D0             [RX UART2]
  GPIO3_A3(11)(12) GPIO3_A1              [LED externo ejemplo]
  GPIO3_A4(13)(14) GND
  GPIO3_A5(15)(16) GPIO3_A6
       3.3V(17)(18) GPIO3_A7
  GPIO4_B2(19)(20) GND         [MOSI SPI0]
  GPIO4_B3(21)(22) GPIO3_B0    [MISO SPI0]
  GPIO4_B0(23)(24) GPIO4_B1    [SCLK SPI0]   [CS0 SPI0]
        GND(25)(26) GPIO4_B4               [CS1 SPI0]
  GPIO4_D1(27)(28) GPIO4_D2
  GPIO0_D4(29)(30) GND
  GPIO0_D5(31)(32) GPIO3_C0
  GPIO3_B2(33)(34) GND
  GPIO3_B3(35)(36) GPIO3_B4
  GPIO3_B6(37)(38) GPIO3_B5
        GND(39)(40) GPIO3_B7
```

> Los números entre paréntesis son los **pines físicos** (1–40). Para calcular el número gpiochipN y offset, usa la fórmula del apartado 2.

### Resumen de funcionalidades y su estado

| Funcionalidad | Estado | Script de ejemplo |
|---|---|---|
| GPIO digital | ✅ Funcional | `Led_test_blink.py` |
| PWM hardware (servo) | ✅ Funcional | `servo_test.py` |
| I2C | ✅ Funcional | `i2c_scan.py`, `OLED_SSD1306.py` |
| SPI | ✅ Funcional | `spi_loopback_test.py` |
| LEDs onboard | ✅ Funcional | `leds_onboard.py` |
| NPU (6 TOPS) | ✅ Funcional | `npu_inference_example.py` |
| GPU (OpenGL 3.0) | ✅ Funcional | — |
| Audio (HDMI / jack) | ✅ Funcional | — |
| WiFi | ✅ Funcional | — |
| Ethernet 2.5GbE | ✅ Funcional | — |
| USB 3.0 / 2.0 | ✅ Funcional | — |
| Cámara MIPI CSI | ⚠️ Sin módulo | — |

---

## Problemas comunes y soluciones

### "Permission denied" al acceder a GPIO/I2C/SPI/PWM

```bash
./setup_gpio_permissions.sh && sudo reboot
```

### El servo no responde / error I/O en `/sys/class/pwm/pwmchip0/export`

El overlay `pwm0-m0` está activo. `setup_gpio_permissions.sh` ya lo cambia a `pwm14-m0`. Si no corriste el script, edita `/boot/orangepiEnv.txt` y reemplaza `pwm0-m0` por `pwm14-m0`, luego reinicia.

### `from rknnlite.api import RKNNLite` falla con ImportError

```bash
./setup_npu.sh
```

### El NPU muestra errores en `dmesg` pero init_runtime() devuelve -1

Asegúrate de llamar `rknn.load_rknn(ruta_al_modelo)` **antes** de `rknn.init_runtime()`.

### `spi.xfer2(enviado)` devuelve los mismos bytes que envié aunque no haya loopback

`xfer2()` modifica la lista de entrada en el lugar. Usa `spi.xfer2(list(enviado))` para pasar una copia.

### La placa no arranca después de editar `/boot/orangepiEnv.txt`

Conecta la placa al PC y monta la partición de arranque para revertir el cambio, o ten una segunda tarjeta SD como respaldo.
