# Capítulo 4 — El Entorno de Desarrollo en Python

## Objetivo

Al finalizar este capítulo el lector tendrá Python configurado con entornos virtuales, instalará las bibliotecas de hardware necesarias para los capítulos siguientes y comprenderá por qué Python es la elección principal para desarrollo en esta placa.

---

## 4.1 Por qué Python para desarrollo embebido en el RK3588

Python no es el lenguaje más rápido en ejecución, pero ofrece ventajas decisivas para el desarrollo en esta plataforma:

**Acceso directo al hardware:** Las bibliotecas `gpiod`, `smbus2`, `spidev` envuelven las llamadas del sistema Linux con una API de alto nivel. El código que controla un GPIO en Python es casi idéntico al que lo hace en C, pero con mucho menos boilerplate.

**Ecosistema de IA:** Las bibliotecas de inferencia del NPU (`rknn-toolkit-lite2`), visión por computador (`opencv-python`) y cómputo numérico (`numpy`) tienen sus APIs principales en Python. El desarrollo de aplicaciones de IA embebida en C requeriría reimplementar funcionalidades que en Python existen con `import`.

**Velocidad de desarrollo:** Para explorar un periférico, probar una conexión I2C o depurar un script de control de servos, el ciclo editar-guardar-ejecutar de Python es significativamente más corto que el ciclo editar-compilar-flashear de C.

**Cuándo usar C en cambio:** Para drivers del kernel, control en tiempo real estricto (jitter < 1 µs), o cuando el rendimiento de la CPU es el cuello de botella. Los capítulos 8–11 cubren programación en C para el kernel.

---

## 4.2 Python en la imagen de Orange Pi

La imagen oficial incluye Python 3.10 como interprete por defecto del sistema:

```bash
python3 --version     # Python 3.10.x
which python3         # /usr/bin/python3

# pip3 para instalar paquetes
pip3 --version
```

> No usar `python` (sin el 3); en Ubuntu 22.04 puede apuntar a Python 2.7 si está instalado, o no existir.

---

## 4.3 Entornos virtuales (venv)

Un entorno virtual es un directorio que contiene una copia aislada del intérprete Python y sus paquetes instalados. Esto permite:
- Tener versiones distintas de una misma biblioteca para proyectos diferentes
- Instalar paquetes sin afectar el sistema operativo
- Reproducir el entorno exacto en otra máquina con `pip freeze`

```bash
# Crear un entorno virtual en el directorio actual
python3 -m venv .venv

# Activar el entorno (el prompt cambia a (.venv))
source .venv/bin/activate

# Verificar que el pip apunta al entorno
which pip                 # debe mostrar .venv/bin/pip

# Instalar paquetes (solo afectan a este entorno)
pip install gpiod smbus2

# Desactivar el entorno
deactivate
```

**Convención de este libro:** los ejemplos de hardware se ejecutan con el Python del sistema (`python3`), sin entorno virtual, porque los paquetes de hardware deben instalarse a nivel de sistema para acceder a los periféricos del kernel correctamente.

---

## 4.4 Instalación de las bibliotecas de hardware

### 4.4.1 Biblioteca de GPIO: gpiod

`gpiod` implementa la API v2 del carácter de dispositivo GPIO del kernel Linux:

```bash
# Instalar la biblioteca Python y las herramientas de línea de comandos
sudo apt install gpiod python3-libgpiod
# O con pip (versión más reciente, API v2):
pip3 install gpiod
```

Verificación:

```bash
# Listar los chips GPIO del sistema
gpiodetect

# Ver las líneas del banco 3
gpioinfo /dev/gpiochip3
```

### 4.4.2 Biblioteca I2C: smbus2

```bash
pip3 install smbus2
```

```python
import smbus2
bus = smbus2.SMBus(2)   # I2C bus 2
datos = bus.read_i2c_block_data(0x3C, 0x00, 4)
bus.close()
```

### 4.4.3 Biblioteca SPI: spidev

```bash
pip3 install spidev
```

### 4.4.4 Control de pantallas OLED: luma.oled

```bash
pip3 install luma.oled
```

Instala automáticamente Pillow (PIL), que provee primitivas de dibujo 2D.

### 4.4.5 Visión por computador: OpenCV

```bash
pip3 install opencv-python numpy
```

> En ARM, la instalación puede tardar varios minutos en compilar extensiones nativas.

### 4.4.6 Runtime de la NPU: rknn-toolkit-lite2

Ver `setup_npu.sh` en la raíz del repositorio. La instalación requiere descargar el wheel específico para Python 3.10 y ARM64:

```bash
./setup_npu.sh
```

### 4.4.7 Resumen de instalación

```bash
pip3 install gpiod smbus2 spidev luma.oled opencv-python numpy
```

---

## 4.5 Primer programa: lectura de temperatura con Python

```python
"""
Lee la temperatura de todas las zonas térmicas del RK3588
y muestra un resumen en pantalla.
"""
import os
import time

BASE = "/sys/class/thermal"

def leer_zonas_termicas():
    zonas = []
    for entrada in sorted(os.listdir(BASE)):
        if not entrada.startswith("thermal_zone"):
            continue
        ruta = f"{BASE}/{entrada}"
        try:
            tipo  = open(f"{ruta}/type").read().strip()
            temp  = int(open(f"{ruta}/temp").read().strip()) // 1000
            zonas.append((tipo, temp))
        except OSError:
            pass
    return zonas

print("Temperaturas del RK3588 (Ctrl+C para salir)")
print("-" * 45)

try:
    while True:
        zonas = leer_zonas_termicas()
        for tipo, temp in zonas:
            print(f"  {tipo:<30} {temp:3d}°C")
        print()
        time.sleep(3)
except KeyboardInterrupt:
    print("Finalizado.")
```

---

## 4.6 Depuración y herramientas útiles

### Ejecutar con salida sin buffer

```bash
# Útil cuando la salida no aparece en tiempo real dentro de scripts o pipes
python3 -u script.py
```

### IPython: REPL mejorado

```bash
pip3 install ipython
ipython3
```

IPython ofrece autocompletado, historial persistente, y la posibilidad de ejecutar comandos del sistema con `!`:

```python
In [1]: import gpiod
In [2]: chips = !gpiodetect
In [3]: chips
```

### pyserial para comunicación UART

```bash
pip3 install pyserial

# Listar puertos disponibles
python3 -m serial.tools.list_ports
```

---

## Resumen del capítulo

- Python 3.10 está disponible de forma nativa en la imagen de Orange Pi. Se accede con `python3`.
- Los entornos virtuales aíslan proyectos pero para desarrollo de hardware se recomienda instalación a nivel sistema.
- Las bibliotecas clave del libro son: `gpiod`, `smbus2`, `spidev`, `luma.oled`, `opencv-python`, `numpy`.
- El patrón `/sys/class/…` permite acceder a periféricos del kernel directamente desde Python sin ninguna biblioteca especial.

## Ejercicios

1. Instale todas las bibliotecas del apartado 4.4 y verifique cada una importándola en el intérprete interactivo (`python3 -c "import gpiod; print(gpiod.__version__)"`).
2. Amplíe el script de temperatura para que registre los valores en un archivo CSV con el formato `timestamp,zona,temperatura` y muestre una alerta visual si alguna zona supera los 75°C.
3. Investigue la diferencia entre `pip install` y `pip3 install` en Ubuntu 22.04. ¿A qué versión de Python apunta cada uno en este sistema?
