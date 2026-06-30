# Capítulo 6 — Comunicación con el Mundo: I2C, SPI y PWM

## Objetivo

Al finalizar este capítulo el lector conectará y controlará periféricos externos mediante los tres protocolos de comunicación más comunes en electrónica embebida: I2C (bus para sensores y pantallas), SPI (bus de alta velocidad) y PWM (control analógico por señal digital).

**Archivos de código:** `03_pwm_servo.py` · `04_i2c_escaneo.py` · `05_i2c_oled.py` · `06_spi_loopback.py`

---

## 6.1 Protocolo I2C

### Fundamentos

I2C (Inter-Integrated Circuit) es un protocolo serie síncrono de dos hilos:
- **SDA** (Serial Data): datos bidireccionales
- **SCL** (Serial Clock): reloj generado por el maestro

Características principales:
- **Topología bus:** múltiples dispositivos comparten los mismos cables
- **Direccionamiento 7 bits:** 112 dispositivos en el mismo bus (0x08–0x77)
- **Open-drain:** los dispositivos solo pueden llevar la línea a bajo; las resistencias de pull-up externas (típicamente 4.7 kΩ) mantienen el nivel alto
- **Velocidades:** 100 kbit/s (estándar), 400 kbit/s (rápido), 1 Mbit/s (rápido-plus)

```
Maestro ──── SDA ──── Esclavo 1 (0x3C)
      │                    │
      └──── SCL ──── Esclavo 2 (0x48)
                           │
                    Resistencias pull-up a 3.3V
```

**Trama I2C:**
```
[START] [ADDR 7 bits] [R/W] [ACK] [DATA 8 bits] [ACK] ... [STOP]
```

El bus I2C-2 del RK3588 está disponible en el cabecero (overlay `i2c2-m0`):
- Pin físico 3 → SDA
- Pin físico 5 → SCL

---

### 6.2 Módulo 4: escaneo del bus I2C

**Archivo:** `04_i2c_escaneo.py`

El proceso de enumeración intenta iniciar una transacción de lectura con cada dirección posible (0x03–0x77). Si el dispositivo responde con ACK, la dirección está ocupada.

```python
import smbus2

bus = smbus2.SMBus(2)    # I2C-2

for direccion in range(0x03, 0x78):
    try:
        bus.read_byte(direccion)   # intentar lectura de 1 byte
        print(f"  Dispositivo en 0x{direccion:02X}")
    except OSError:
        pass   # NACK: no hay nadie en esta dirección

bus.close()
```

```bash
python3 04_i2c_escaneo.py
```

**Direcciones comunes de dispositivos I2C:**

| Dirección | Dispositivo típico |
|---|---|
| 0x3C / 0x3D | Pantalla OLED SSD1306 |
| 0x48 – 0x4B | ADC ADS1115 |
| 0x68 / 0x69 | IMU MPU-6050 |
| 0x76 / 0x77 | Sensor BMP280/BME280 |
| 0x27 | Expander I/O PCF8574 |

---

### 6.3 Módulo 5: pantalla OLED SSD1306

**Archivo:** `05_i2c_oled.py`  
**Hardware:** Módulo OLED 128×64 px con controlador SSD1306

**Conexión:**
```
   Orange Pi 5 Plus              Módulo OLED SSD1306
   (cabecero 40 pines)                (128×64 px)

   Pin 1  (3.3V) ──────────────────  VCC
   Pin 6  (GND)  ──────────────────  GND
   Pin 3  (SDA, I2C2) ─────────────  SDA
   Pin 5  (SCL, I2C2) ─────────────  SCL

         ┌────────────────────┐
   3.3V ─┤ VCC            SDA ├──── Pin 3
    GND ─┤ GND            SCL ├──── Pin 5
         │   ┌──────────┐     │
         │   │ display  │     │
         │   │ 128 × 64 │     │
         │   └──────────┘     │
         └────────────────────┘
```

> Bus I2C-2 compartido: cualquier otro sensor I2C (BME280, MPU-6050, etc.) puede conectarse en paralelo a los mismos pines 3 y 5, siempre que su dirección no colisione con 0x3C.

**Pila de software:**
```
Python (código del usuario)
    ↓
luma.oled  →  ssd1306()  →  canvas()  →  ImageDraw (Pillow)
    ↓
luma.core  →  i2c()  →  smbus2
    ↓
Kernel  →  i2c-dev  →  driver i2c-rk3x
    ↓
Hardware SSD1306 (I2C bus 2, dirección 0x3C)
```

**Canvas como gestor de contexto:**
```python
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

serial     = i2c(port=2, address=0x3C)
dispositivo = ssd1306(serial)

with canvas(dispositivo) as dibujo:
    dibujo.text((0, 0),  "Hola, mundo",    fill="white")
    dibujo.text((0, 16), "Orange Pi 5+",   fill="white")
    dibujo.rectangle([0, 48, 127, 63],     outline="white")
# Al salir del bloque, se transfiere el framebuffer al SSD1306
```

**Primitivas de dibujo disponibles (Pillow ImageDraw):**

```python
dibujo.text((x, y), "texto", fill="white", font=fuente)
dibujo.line([x1, y1, x2, y2], fill="white", width=1)
dibujo.rectangle([x1, y1, x2, y2], outline="white", fill="black")
dibujo.ellipse([x1, y1, x2, y2], outline="white")
dibujo.point((x, y), fill="white")
```

```bash
pip3 install luma.oled
python3 05_i2c_oled.py
```

---

## 6.4 Protocolo SPI

### Fundamentos

SPI (Serial Peripheral Interface) es un protocolo serie síncrono full-duplex de cuatro señales:

| Señal | Dirección | Descripción |
|---|---|---|
| MOSI | Maestro → Esclavo | Master Out Slave In |
| MISO | Esclavo → Maestro | Master In Slave Out |
| SCLK | Maestro | Reloj |
| CS | Maestro | Chip Select (activo en bajo) |

**Full-duplex:** en cada ciclo de reloj se transfiere un bit en cada dirección simultáneamente. El maestro envía y recibe en paralelo.

**Modos de operación (CPOL/CPHA):**

| Modo | CPOL | CPHA | Reloj en reposo | Muestreo |
|---|---|---|---|---|
| 0 | 0 | 0 | Bajo | Flanco de subida |
| 1 | 0 | 1 | Bajo | Flanco de bajada |
| 2 | 1 | 0 | Alto | Flanco de bajada |
| 3 | 1 | 1 | Alto | Flanco de subida |

El modo 0 es el más común (sensores de temperatura, memorias Flash, pantallas).

**Pines en el cabecero (overlay `spi0-m2-cs0-cs1-spidev`):**

| Pin físico | Función | Dispositivo |
|---|---|---|
| 19 | MOSI | /dev/spidev0.x |
| 21 | MISO | |
| 23 | SCLK | |
| 24 | CS0 | /dev/spidev0.0 |
| 26 | CS1 | /dev/spidev0.1 |

---

### 6.5 Módulo 6: prueba de loopback SPI

**Archivo:** `06_spi_loopback.py`  
**Hardware opcional:** puente entre pin 19 (MOSI) y pin 21 (MISO)

### El circuito

```
   Cabecero de 40 pines
   ┌──────────────────────┐
   │ ⋮                    │
   │19 ●── MOSI           │
   │20 ●   GND            │
   │21 ●── MISO ──┐       │
   │22 ●          │       │
   │23 ●   SCLK   │       │  puente (jumper)
   │24 ●   CS0    │       │  directo entre
   │ ⋮            │       │  pin 19 y pin 21
   └──────────────┼───────┘
                  │
        pin 19 ───┘ (cable corto, sin componentes)
```

Sin esclavo conectado, el puente entre MOSI y MISO hace que cada byte transmitido regrese inmediatamente al maestro, permitiendo validar el bus sin hardware adicional.

**Advertencia crítica sobre `spidev.xfer2()`:**

```python
import spidev
spi = spidev.SpiDev()
spi.open(0, 0)

enviado = [0xAA, 0x55, 0xFF]

# INCORRECTO: xfer2 modifica la lista de entrada in-place
recibido = spi.xfer2(enviado)
# Ahora enviado == recibido (misma referencia), la comparación es trivialmente True

# CORRECTO: pasar una copia
recibido = spi.xfer2(list(enviado))
# Ahora enviado conserva los datos originales para comparar
```

Esto es un comportamiento documentado de la API pero frecuentemente pasado por alto. Ignorarlo produce errores de validación silenciosos.

```bash
python3 06_spi_loopback.py
```

```
Bus SPI-0 inicializado.  Velocidad: 500 kHz  Modo: 0
Trama enviada  : ['0x0', '0x1', '0x55', '0xaa', '0xff']
Trama recibida : ['0x0', '0x1', '0x55', '0xaa', '0xff']

Resultado: LOOPBACK VERIFICADO
```

---

## 6.6 Modulación por Ancho de Pulso (PWM)

### Fundamentos

PWM genera una señal digital periódica definida por:
- **Período T:** inverso de la frecuencia
- **Duty cycle:** fracción de tiempo en estado alto

```
       ┌───┐   ┌───┐   ┌───┐
       │   │   │   │   │   │
───────┘   └───┘   └───┘   └────
  |<──T──>|
  |< t_alto >|

duty_cycle = t_alto / T × 100%
```

**Aplicaciones:**
- **Servo motors:** frecuencia fija 50 Hz, posición angular determinada por el ancho del pulso
- **Control de velocidad de motores DC:** duty cycle determina la potencia media
- **Dimmer de LED:** duty cycle determina el brillo percibido (sin parpadeo visible > 50 Hz)
- **Generación de señales analógicas:** con un filtro paso-bajo, PWM produce una señal analógica

### El problema del overlay pwm0-m0

La imagen oficial activa por defecto el overlay `pwm0-m0`, que controla el pin GPIO0_15. Este pin está físicamente compartido con el bus I2C interno `feaa0000.i2c`, que lo reclama primero durante el arranque:

```
[    5.234] rockchip-pinctrl: pin gpio0-15 already requested by feaa0000.i2c
```

**Solución:** usar el overlay `pwm14-m0`, que controla el pin físico 7 del cabecero. `setup_gpio_permissions.sh` realiza este cambio automáticamente en `/boot/orangepiEnv.txt`.

### La interfaz sysfs de PWM

```
/sys/class/pwm/pwmchip2/     ← controlador hardware (overlay pwm14-m0)
    npwm                      ← cuántos canales (1)
    export                    ← escribir "0" crea pwm0/
    pwm0/
        period      [ns]      ← período total (20000000 = 20 ms = 50 Hz)
        duty_cycle  [ns]      ← tiempo en alto (1500000 = 1.5 ms = centro)
        enable                ← "1" activa, "0" desactiva
```

### Servomotores de radio control

Un servo estándar (SG90, MG996R) interpreta la señal PWM de la siguiente manera:

| Ancho de pulso | Posición angular |
|---|---|
| 0.5 ms (500 µs) | ~0° (mínimo) |
| 1.5 ms (1500 µs) | ~90° (centro) |
| 2.5 ms (2500 µs) | ~180° (máximo) |

El período siempre es 20 ms (50 Hz). Es el ancho absoluto del pulso, no el porcentaje, lo que determina la posición.

---

### 6.7 Módulo 3: control de servomotor

**Archivo:** `03_pwm_servo.py`  
**Hardware:** Servomotor conectado al pin físico 7 (PWM14)

**Conexión:**
```
   Orange Pi 5 Plus                 Servomotor SG90
   (cabecero 40 pines)            (3 cables: rojo/negro/señal)

   Pin 2  (5V)   ───────────────────  rojo    (VCC)
   Pin 6  (GND)  ───────────────────  negro   (GND)
   Pin 7  (PWM14)───────────────────  amarillo (señal)

         ┌───────────────┐         ┌──────────┐
    5V ──┤ rojo          │         │   ╱│      │
   GND ──┤ negro    SG90 ├─────────┤  ╱ │ eje  │
  PWM14──┤ amarillo      │         │ ╱  │      │
         └───────────────┘         └──────────┘
```

> **Importante:** el SoC entrega 3.3 V máx. por pin, pero el servo necesita 5 V para su motor interno — solo el cable de **señal** (amarillo) va al pin PWM; la alimentación (rojo) debe tomarse del pin de 5V, nunca del pin PWM.

**Código núcleo:**

```python
import os, time

CHIP_PWM   = "/sys/class/pwm/pwmchip2"
CANAL_PWM  = f"{CHIP_PWM}/pwm0"
PERIODO_NS = 20_000_000   # 20 ms = 50 Hz

def escribir(ruta, valor):
    with open(ruta, "w") as f:
        f.write(str(valor))

# Exportar canal si no existe
if not os.path.isdir(CANAL_PWM):
    escribir(f"{CHIP_PWM}/export", 0)
    time.sleep(0.2)

escribir(f"{CANAL_PWM}/period",    PERIODO_NS)
escribir(f"{CANAL_PWM}/enable",    1)
escribir(f"{CANAL_PWM}/duty_cycle", 1_500_000)  # centro: 1.5 ms
```

**Verificar que el overlay está activo:**

```bash
cat /boot/orangepiEnv.txt | grep pwm
# Debe mostrar: overlays=... pwm14-m0 ...

# Ver qué pwmchip corresponde al overlay pwm14
cat /sys/class/pwm/pwmchip*/device/uevent | grep -B1 DRIVER
```

```bash
python3 03_pwm_servo.py
```

---

## Resumen del capítulo

- **I2C** usa dos hilos (SDA/SCL) para comunicar múltiples dispositivos en un bus compartido mediante direcciones de 7 bits.
- **SPI** usa cuatro hilos (MOSI/MISO/SCLK/CS) para comunicación full-duplex de alta velocidad, con un CS por dispositivo.
- **PWM** genera señales periódicas cuyo duty cycle o ancho de pulso controla periféricos analógicos como servos y motores.
- El overlay `pwm0-m0` de la imagen oficial es inoperable; el correcto es `pwm14-m0` (pin físico 7).
- `spidev.xfer2()` modifica la lista de entrada in-place; siempre pasar una copia.

## Ejercicios

1. Conecte un sensor de temperatura BMP280 al bus I2C-2 (pines 3 y 5). Use `04_i2c_escaneo.py` para confirmar que responde en 0x76 o 0x77. Instale `pip3 install adafruit-circuitpython-bmp280` y lea la temperatura cada segundo.
2. Modifique `03_pwm_servo.py` para que el servo realice un barrido automático de 0° a 180° y vuelta, con paso de 5° y pausa de 50 ms entre posiciones.
3. Implemente un loopback SPI a 2 MHz con modo 3 (CPOL=1, CPHA=1) y verifique que los datos siguen retornando íntegros. ¿Cambia el tiempo de transmisión respecto a 500 kHz?
