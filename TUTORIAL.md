# Guía académica: Orange Pi 5 Plus (RK3588)
## Desarrollo de sistemas embebidos con Linux y Python

---

## Índice

1. [Arquitectura del sistema](#1-arquitectura-del-sistema)
2. [Configuración del entorno](#2-configuración-del-entorno)
3. [Módulo 1 y 2: Subsistema GPIO](#3-módulos-1-y-2-subsistema-gpio)
4. [Módulo 3: Modulación por Ancho de Pulso (PWM)](#4-módulo-3-modulación-por-ancho-de-pulso-pwm)
5. [Módulos 4 y 5: Protocolo I2C](#5-módulos-4-y-5-protocolo-i2c)
6. [Módulo 6: Protocolo SPI](#6-módulo-6-protocolo-spi)
7. [Módulo 7: Subsistema LED del kernel](#7-módulo-7-subsistema-led-del-kernel)
8. [Módulo 8: Unidad de Procesamiento Neuronal (NPU)](#8-módulo-8-unidad-de-procesamiento-neuronal-npu)
9. [Apéndice A: Cabecero de 40 pines](#apéndice-a-cabecero-de-40-pines)
10. [Apéndice B: Diagnóstico y resolución de problemas](#apéndice-b-diagnóstico-y-resolución-de-problemas)

---

## 1. Arquitectura del sistema

### 1.1 El SoC RK3588

El Rockchip RK3588 es un sistema en chip (SoC) de arquitectura heterogénea diseñado para aplicaciones de computación embebida de alto rendimiento. Incorpora en un único die los siguientes procesadores especializados:

**CPU (big.LITTLE)**  
Implementa la topología DynamIQ de ARM, con dos clústeres de diferente rendimiento y eficiencia energética:
- Clúster de alto rendimiento: 4× Cortex-A76 @ 2.4 GHz
- Clúster de alta eficiencia: 4× Cortex-A55 @ 1.8 GHz

El planificador del kernel asigna tareas a uno u otro clúster según la carga y la política de energía activa (schedutil, ondemand, powersave, performance).

**GPU Mali-G610 MP4**  
Implementa la arquitectura Valhall de ARM. El driver de espacio de usuario en Linux es Panfrost (código abierto), que expone OpenGL ES 3.1 y OpenGL 3.0 mediante la capa de compatibilidad de Mesa.

**NPU (Neural Processing Unit)**  
Tres núcleos independientes de 2 TOPS cada uno, para un total de 6 TOPS (INT8). El driver del kernel es el módulo `rknpu`, propiedad de Rockchip y distribuido bajo el árbol BSP.

**VPU (Video Processing Unit)**  
Decodificación hardware de H.265/H.264/VP9/AV1 hasta 8K@60fps. El acceso desde espacio de usuario requiere los componentes Rockchip Media Process Platform (RKMPP), incluidos en la imagen oficial.

### 1.2 El kernel BSP y sus implicaciones

La imagen oficial de Orange Pi utiliza un kernel **BSP** (Board Support Package) mantenido por Rockchip en la rama `5.10.x`, no el kernel mainline de kernel.org. Esto tiene implicaciones directas:

- Los drivers del NPU (`rknpu`), VPU (`rkmpp`) y otros periféricos propietarios solo existen en este árbol BSP.
- El kernel mainline (≥6.x) tiene soporte parcial y creciente para el RK3588, pero sin los drivers propietarios.
- 41 paquetes del sistema están retenidos con `apt-mark hold` para prevenir actualizaciones que romperían los componentes vendor (mesa, ffmpeg, rkmpp, wiringpi, etc.).

```bash
apt-mark showhold   # lista los 41 paquetes retenidos intencionalmente
```

### 1.3 Device Tree y overlays

El árbol de dispositivos (Device Tree, DT) es la estructura de datos que describe al kernel el hardware de la placa: qué periféricos existen, en qué direcciones de bus están mapeados, qué interrupciones usan y cómo se interconectan.

Los **overlays** son fragmentos de Device Tree que se aplican al árbol base en tiempo de arranque para habilitar o reconfigurar periféricos. En la Orange Pi 5 Plus se configuran en:

```
/boot/orangepiEnv.txt
```

```
overlays=i2c2-m0 pwm14-m0 spi0-m2-cs0-cs1-spidev
```

Cada overlay habilita un periférico y lo asigna a un multiplexado de pines específico (sufijo `-m0`, `-m1`, etc. indica el grupo de pines del RK3588 al que se enruta la señal).

---

## 2. Configuración del entorno

### 2.1 Por qué es necesaria la configuración inicial

Por defecto, en la imagen oficial de Orange Pi:
- Los archivos `/dev/gpiochip*` pertenecen a `root:root`.
- Los archivos `/dev/i2c-*` tienen grupo `i2c` pero el usuario no pertenece a ese grupo.
- El grupo `spi` no existe.
- El canal PWM14 necesita quedar exportado con permisos para el grupo `gpio`.

### 2.2 setup_gpio_permissions.sh

Este script realiza las siguientes operaciones (todas son idempotentes):

1. Crea los grupos `gpio`, `i2c` y `spi` si no existen.
2. Agrega el usuario actual a esos tres grupos.
3. Instala `gpiod` (herramientas de línea de comandos de libgpiod).
4. Escribe reglas udev en `/etc/udev/rules.d/` para asignar los grupos correctos a `/dev/gpiochip*` y `/dev/spidev*`.
5. Configura `/boot/orangepiEnv.txt` con `i2c2-m0`, `pwm14-m0` y `spi0-m2-cs0-cs1-spidev`.
6. Crea e instala el servicio systemd `pwm-setup.service`, que en cada arranque exporta el canal PWM y le asigna permisos de grupo.

```bash
./setup_gpio_permissions.sh
sudo reboot
```

### 2.3 setup_npu.sh

Descarga e instala los componentes mínimos del stack RKNN directamente desde el repositorio oficial de Rockchip (`airockchip/rknn-toolkit2`), sin clonar el repositorio completo (≈3.8 GB):

- Wheel `rknn_toolkit_lite2-2.x.x-cpXXX-linux_aarch64.whl` → instala `rknnlite`.
- Biblioteca compartida `librknnrt.so` → runtime C que interface con el driver `rknpu`.

```bash
./setup_npu.sh
```

---

## 3. Módulos 1 y 2: Subsistema GPIO

### 3.1 Fundamentos del subsistema GPIO en Linux

**Organización del hardware**

El RK3588 organiza sus líneas GPIO en bancos numerados del 0 al 5. Cada banco gestiona hasta 32 líneas distribuidas en cuatro grupos de 8 bits: A, B, C y D. La notación `GPIOx_Yn` identifica el banco `x`, el grupo `Y` (A–D) y el bit `n` (0–7).

La fórmula para obtener el número global (offset) de cualquier línea es:

```
offset = banco × 32 + (letra − A) × 8 + bit

Ejemplos:
  GPIO3_A1  =  3 × 32 + 0 × 8 + 1  =  97
  GPIO4_B2  =  4 × 32 + 1 × 8 + 2  =  138
```

**GPIO Character Device**

El kernel Linux expone cada banco como un character device en `/dev/gpiochipN`. Las operaciones de configuración y E/S se realizan mediante llamadas `ioctl()` al descriptor de archivo:

- `GPIO_V2_GET_LINEINFO_IOCTL` — consultar el estado de una línea
- `GPIO_V2_GET_LINE_IOCTL` — solicitar una o más líneas con configuración
- `GPIO_V2_LINE_SET_VALUES_IOCTL` — escribir valores de salida
- `GPIO_V2_LINE_GET_VALUES_IOCTL` — leer valores de entrada

**libgpiod v2**

La biblioteca libgpiod encapsula las llamadas `ioctl()` y provee una API segura en C y Python. A diferencia del acceso directo a `/dev/mem` (empleado por wiringpi), solo otorga acceso a las líneas explícitamente solicitadas, sin exponer el espacio de memoria completo del sistema.

### 3.2 Módulo 1: salida digital (`01_gpio_salida.py`)

Configura GPIO3_A1 (pin físico 12) como salida y alterna su nivel cada segundo.

**Construcción del circuito:**

```
Pin físico 12 (GPIO3_A1) ──┤ 330 Ω ├──┤ LED ├──── Pin físico 6 (GND)
                              ánodo       cátodo
```

La resistencia limita la corriente: con V_out = 3.3 V y V_f ≈ 2.0 V (LED rojo):

```
I = (3.3 - 2.0) / 330 = 3.9 mA   (seguro, máx. recomendado 12 mA)
```

**Ejecución:**
```bash
python3 01_gpio_salida.py
```

**Resultados esperados:**
```
Línea GPIO3_A1 adquirida en modo salida.
Presione Ctrl+C para terminar.

Ciclo 0001 — ALTO  (3.3 V)
Ciclo 0001 — BAJO  (0 V)
Ciclo 0002 — ALTO  (3.3 V)
...
```

### 3.3 Módulo 2: entrada digital con detección de flancos (`02_gpio_entrada.py`)

Configura GPIO3_A4 (pin físico 13) como entrada con pull-up interno y captura eventos de flanco mediante la interfaz bloqueante de libgpiod v2.

**Comportamiento del bucle de eventos:**

`request.read_edge_events()` es un iterador bloqueante: la ejecución queda suspendida hasta que el hardware detecta una transición en la línea. No hay consumo de CPU activo entre eventos.

**Ejecución:**
```bash
python3 02_gpio_entrada.py
```

**Resultados esperados:**
```
  [   23.842100 s]  Flanco de BAJADA  → pulsador presionado
  [   24.301547 s]  Flanco de SUBIDA  → pulsador soltado
```

---

## 4. Módulo 3: Modulación por Ancho de Pulso (PWM)

### 4.1 Principio de funcionamiento

La modulación por ancho de pulso (PWM) produce una señal digital periódica descrita por su período T y su tiempo en estado alto t_alto. El duty cycle expresa la fracción de tiempo en estado alto:

```
duty_cycle [%] = (t_alto / T) × 100
```

Para cargas resistivas (LEDs, calentadores), el duty cycle determina la potencia media entregada. Para servomotores, el ancho absoluto del pulso (no el porcentaje) determina la posición angular.

### 4.2 Control de servomotores

Los servomotores de radio control incorporan un circuito de control en lazo cerrado que interpreta la señal PWM de la siguiente manera:

```
Período fijo:  T = 20 ms (50 Hz)
Pulso mínimo:  t = 0.5 ms  →  posición ≈ 0°
Pulso central: t = 1.5 ms  →  posición ≈ 90°
Pulso máximo:  t = 2.5 ms  →  posición ≈ 180°
```

El circuito interno mide el ancho del pulso, lo compara con la posición actual del potenciómetro acoplado al eje y acciona el motor hasta reducir el error a cero (control proporcional). Este proceso ocurre de forma completamente independiente del procesador principal.

### 4.3 La interfaz sysfs del kernel PWM

```
/sys/class/pwm/pwmchip2/          ← controlador hardware (overlay pwm14-m0)
    npwm                           ← 1: un canal disponible
    export                         ← escribir "0" crea pwm0/
    pwm0/
        period        [ns]         ← escribir 20000000 → 20 ms → 50 Hz
        duty_cycle    [ns]         ← escribir 1500000  → 1.5 ms → 90°
        enable                     ← escribir "1" activa la señal
```

### 4.4 Ejecución del módulo 3 (`03_pwm_servo.py`)

**Conexión:**
```
Pin físico 2 (5V)    → cable rojo   (VCC del servo)
Pin físico 6 (GND)   → cable negro  (GND del servo)
Pin físico 7 (PWM14) → cable amarillo/blanco (señal)
```

```bash
python3 03_pwm_servo.py
```

```
Servomotor inicializado.
  Período : 20 ms  (50 Hz)
  Rango   : 500 µs – 2500 µs  (centro: 1500 µs)

Ancho de pulso en µs [500–2500]: 1500
  → duty cycle: 7.50%  (1500 µs / 20 ms)
Ancho de pulso en µs [500–2500]: 500
  → duty cycle: 2.50%  (500 µs / 20 ms)
```

---

## 5. Módulos 4 y 5: Protocolo I2C

### 5.1 Características del protocolo I2C

I2C es un protocolo serie síncrono de dos hilos con las siguientes características de diseño:

**Topología:** bus compartido. Múltiples maestros y esclavos comparten las mismas líneas SDA y SCL. El arbitraje del bus se implementa en hardware mediante la naturaleza open-drain de las líneas.

**Open-drain:** Los dispositivos solo pueden llevar la línea a estado bajo (conectando a GND mediante un transistor). Para el estado alto, la línea es liberada y la resistencia de pull-up externa eleva la tensión a VCC. Esto garantiza que si dos dispositivos intentan transmitir simultáneamente, la línea resultante sea el AND lógico de sus valores, evitando cortocircuitos.

**Velocidades definidas por la especificación:**

| Modo | Velocidad |
|---|---|
| Estándar | 100 kbit/s |
| Rápido | 400 kbit/s |
| Rápido Plus | 1 Mbit/s |
| Alta velocidad | 3.4 Mbit/s |

**Direccionamiento:** 7 bits por defecto (112 direcciones utilizables). Existe un modo extendido de 10 bits.

**Trama de datos:**
```
[START] [ADDR(7)] [R/W] [ACK] [DATA(8)] [ACK] ... [STOP]
```

### 5.2 Módulo 4: enumeración del bus (`04_i2c_escaneo.py`)

El proceso de escaneo envía una trama de lectura a cada dirección del rango 0x03–0x77. La presencia de un ACK en la línea SDA indica que existe un dispositivo en esa dirección.

```bash
python3 04_i2c_escaneo.py        # bus I2C-2 (por defecto)
python3 04_i2c_escaneo.py 7      # bus I2C-7
```

**Con una pantalla OLED SSD1306 conectada:**
```
Escaneando I2C-2  (rango 0x03 – 0x77)
--------------------------------------------------
Dispositivos detectados: 1
    0x3C  (decimal  60)
```

### 5.3 Módulo 5: pantalla OLED SSD1306 (`05_i2c_oled.py`)

El controlador SSD1306 requiere una secuencia de inicialización de comandos antes de aceptar datos de display. La biblioteca luma.oled gestiona esta inicialización de forma automática.

**Secuencia interna al abrir el canvas:**
1. `canvas(device).__enter__()` crea una imagen PIL vacía del tamaño del display.
2. El código del usuario dibuja sobre el objeto ImageDraw.
3. `canvas(device).__exit__()` convierte la imagen PIL al formato de páginas del SSD1306 y la transfiere por I2C.

```bash
pip3 install luma.oled
python3 05_i2c_oled.py
```

---

## 6. Módulo 6: Protocolo SPI

### 6.1 Características del protocolo SPI

SPI es un protocolo serie síncrono full-duplex basado en un registro de desplazamiento compartido entre maestro y esclavo. En cada ciclo de reloj:

- El maestro desplaza un bit desde su registro de salida hacia MOSI.
- El esclavo desplaza un bit desde su registro de salida hacia MISO.
- Ambos registros se actualizan simultáneamente.

**Ventajas respecto a I2C:**
- Mayor velocidad (decenas de MHz vs. 400 kHz típico de I2C).
- Comunicación full-duplex genuina.
- Sin mecanismo de arbitraje (bus dedicado por esclavo).

**Desventajas:**
- Requiere una línea CS por cada esclavo.
- No tiene mecanismo estándar de detección de dispositivos.

### 6.2 Configuración de pines SPI-0

El overlay `spi0-m2-cs0-cs1-spidev` enruta el bus SPI-0 al grupo de pines M2:

| Función | Pin físico | Dispositivo |
|---|---|---|
| MOSI | 19 | `/dev/spidev0.x` |
| MISO | 21 | |
| SCLK | 23 | |
| CS0 | 24 | `/dev/spidev0.0` |
| CS1 | 26 | `/dev/spidev0.1` |

### 6.3 Módulo 6: prueba de loopback (`06_spi_loopback.py`)

Para el loopback completo, conectar con un puente el pin 19 (MOSI) con el pin 21 (MISO).

```bash
python3 06_spi_loopback.py
```

**Con puente MOSI-MISO:**
```
Bus SPI-0 inicializado.  Velocidad: 500 kHz  Modo: 0
Trama enviada  : ['0x0', '0x1', '0x55', '0xaa', '0xff']
Trama recibida : ['0x0', '0x1', '0x55', '0xaa', '0xff']

Resultado: LOOPBACK VERIFICADO
```

---

## 7. Módulo 7: Subsistema LED del kernel

### 7.1 Arquitectura del subsistema leds

El subsistema LED de Linux implementa una capa de abstracción entre los drivers de hardware de LEDs (GPIO, PWM, I2C) y las políticas de control. Su diseño separa el **qué controla** (el driver) del **cómo decide** (el trigger).

**Estructura en sysfs:**
```
/sys/class/leds/<nombre>/
    brightness       — nivel de brillo (escritura/lectura)
    max_brightness   — valor máximo (solo lectura)
    trigger          — trigger activo (escritura/lectura)
```

**Triggers disponibles en la imagen Orange Pi:**

| Trigger | Comportamiento |
|---|---|
| `none` | Control manual desde espacio de usuario |
| `heartbeat` | Parpadeo proporcional a la carga del CPU |
| `timer` | Parpadeo a frecuencia fija (configurable) |
| `phy0tx` | Actividad de transmisión WiFi |
| `mmc0` | Actividad de la tarjeta SD |
| `cpu0`–`cpu7` | Actividad de cada núcleo del CPU |

### 7.2 Ejecución del módulo 7 (`07_leds_integrados.py`)

```bash
python3 07_leds_integrados.py
```

El script transfiere el control de `green_led` y `blue_led` al proceso, ejecuta una secuencia de parpadeo, y restaura el trigger `heartbeat` al terminar.

---

## 8. Módulo 8: Unidad de Procesamiento Neuronal (NPU)

### 8.1 Arquitectura de la NPU RK3588

La NPU del RK3588 consta de tres núcleos idénticos de 2 TOPS cada uno. Cada núcleo implementa un array sistólico de unidades multiply-accumulate (MAC) optimizado para operaciones de convolución con pesos cuantizados a INT8.

El rendimiento de 6 TOPS significa que la NPU puede ejecutar 6 × 10¹² operaciones de multiplicación-acumulación de enteros de 8 bits por segundo. Para comparación, un Cortex-A76 ejecuta ≈ 4 GOPS (4 × 10⁹) mediante extensiones NEON.

**Ventaja de la NPU para inferencia CNN:**
Una red como ResNet-18 requiere aproximadamente 1.8 × 10⁹ multiplicaciones-acumulaciones (MACs) por imagen. Ejecutada en la CPU tarda ≈ 450 ms; en la NPU, con cuantización INT8, ≈ 5–10 ms.

### 8.2 El ecosistema RKNN

```
                  ┌─────────────────────────────────────┐
                  │  DESARROLLO  (PC x86-64)            │
                  │  rknn-toolkit2                      │
                  │  PyTorch / ONNX / TF  ──►  .rknn   │
                  └──────────────────┬──────────────────┘
                                     │  transferir .rknn a la placa
                  ┌──────────────────▼──────────────────┐
                  │  INFERENCIA  (Orange Pi 5 Plus)     │
                  │  rknn-toolkit-lite2 (Python)        │
                  │  RKNNLite.inference()               │
                  │       ↓                             │
                  │  librknnrt.so (runtime C)           │
                  │       ↓                             │
                  │  driver rknpu (kernel BSP 5.10)     │
                  │       ↓                             │
                  │  NPU hardware (6 TOPS)              │
                  └─────────────────────────────────────┘
```

### 8.3 Flujo de inferencia y orden obligatorio de llamadas

```python
rknn = RKNNLite()
rknn.load_rknn("modelo.rknn")   # 1. Deserializar modelo en RAM
rknn.init_runtime()              # 2. Inicializar driver (DESPUÉS de load_rknn)
rknn.inference(inputs=[tensor])  # 3. Ejecutar en NPU
rknn.release()                   # 4. Liberar recursos
```

`init_runtime()` necesita conocer las dimensiones y tipos de los tensores de entrada/salida para dimensionar los buffers DMA. Esta información solo existe después de `load_rknn()`. Invocar `init_runtime()` antes produce código de retorno -1.

### 8.4 Conversión de un modelo propio

En un PC con Ubuntu 22.04 y Python 3.8–3.10:

```bash
pip install rknn-toolkit2
```

```python
from rknn.api import RKNN

rknn = RKNN(verbose=True)
rknn.config(target_platform="rk3588", mean_values=[[128, 128, 128]],
            std_values=[[128, 128, 128]])
rknn.load_onnx(model="mi_red.onnx")
rknn.build(do_quantization=True, dataset="imagenes_calibracion.txt")
rknn.export_rknn("mi_red_rk3588.rknn")
rknn.release()
```

El archivo de calibración contiene rutas a 50–200 imágenes representativas del dominio del modelo. La cuantización post-entrenamiento calibra los rangos de activaciones para minimizar la pérdida de precisión al pasar de FP32 a INT8.

### 8.5 Ejecución del módulo 8 (`08_npu_inferencia.py`)

```bash
python3 08_npu_inferencia.py
```

**Salida esperada (primera ejecución):**
```
=== Inferencia de imagen en el NPU RK3588 ===

1. Verificando archivos necesarios...
  Descargando resnet18_for_rk3588.rknn ...
  11.4 MB descargados.
  Descargando space_shuttle_224.jpg ...
  0.2 MB descargados.
2. Cargando modelo ResNet-18 compilado para RK3588...
3. Inicializando runtime del NPU (rknpu)...
   Runtime inicializado correctamente.
4. Preparando tensor de entrada...
   Tensor: forma (1, 224, 224, 3), dtype uint8
5. Ejecutando inferencia en el NPU...

=== Resultado ===
  Clase predicha (índice ImageNet) : 812
  Puntaje de confianza             : 11.5938
  Clase 812 en ImageNet            : 'space shuttle'
  Clasificación correcta.
```

---

## Apéndice A: Cabecero de 40 pines

```
       3.3V  (1) (2)  5V
  I2C2_SDA  (3) (4)  5V          GPIO0_C1
  I2C2_SCL  (5) (6)  GND         GPIO0_B6
     PWM14  (7) (8)  UART2_TX    GPIO0_C0 / GPIO0_D1
       GND  (9)(10)  UART2_RX    GPIO0_D0
  GPIO3_A3 (11)(12)  GPIO3_A1
  GPIO3_A4 (13)(14)  GND
  GPIO3_A5 (15)(16)  GPIO3_A6
      3.3V (17)(18)  GPIO3_A7
  SPI0_MOSI(19)(20)  GND         GPIO4_B2
  SPI0_MISO(21)(22)  GPIO3_B0    GPIO4_B3
  SPI0_SCLK(23)(24)  SPI0_CS0    GPIO4_B0 / GPIO4_B1
       GND (25)(26)  SPI0_CS1    GPIO4_B4
  GPIO4_D1 (27)(28)  GPIO4_D2
  GPIO0_D4 (29)(30)  GND
  GPIO0_D5 (31)(32)  GPIO3_C0
  GPIO3_B2 (33)(34)  GND
  GPIO3_B3 (35)(36)  GPIO3_B4
  GPIO3_B6 (37)(38)  GPIO3_B5
       GND (39)(40)  GPIO3_B7
```

Los números entre paréntesis corresponden a la numeración física del cabecero (1–40).

---

## Apéndice B: Diagnóstico y resolución de problemas

### B.1 Error de permisos al acceder a periféricos

**Síntoma:**
```
PermissionError: [Errno 13] Permission denied: '/dev/gpiochip3'
```

**Causa:** El usuario no pertenece al grupo `gpio`. Aplica también a `i2c` y `spi`.

**Verificación:**
```bash
groups                            # lista los grupos del usuario actual
ls -la /dev/gpiochip*             # verifica propietario y modo del device
```

**Solución:**
```bash
./setup_gpio_permissions.sh && sudo reboot
```

### B.2 Mensajes RKNPU en dmesg

**Síntoma:**
```
RKNPU: can't request region for resource [mem 0xfdab0000-0xfdabffff]
failed to initialize power model
```

**Causa:** Defecto de implementación en el árbol BSP 5.10. El driver intenta reservar una región de memoria que ya está marcada como no disponible en el Device Tree.

**Impacto:** Ninguno sobre la funcionalidad. La NPU opera con plena capacidad.

**Referencia:** Reportado en `github.com/orangepi-xunlong/linux-orangepi/issues/88`.

### B.4 init_runtime() retorna -1

**Causa:** Se invocó `init_runtime()` antes de `load_rknn()`.

**Solución:** El orden correcto es obligatorio:
```python
rknn.load_rknn("modelo.rknn")   # primero
rknn.init_runtime()              # segundo
```

### B.5 spidev.xfer2() produce comparaciones incorrectas

**Síntoma:** `recibido == enviado` es siempre `True` aunque no haya loopback.

**Causa:** `xfer2()` modifica la lista de entrada in-place y retorna la misma referencia. Tras la llamada, `enviado` y `recibido` apuntan al mismo objeto.

**Solución:**
```python
recibido = spi.xfer2(list(enviado))   # pasar una copia
```
