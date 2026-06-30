# Capítulo 5 — El Corazón de la Electrónica: GPIO

## Objetivo

Al finalizar este capítulo el lector controlará una línea GPIO como salida digital (LED) y leerá una entrada digital con detección de flancos (pulsador), comprendiendo la arquitectura del subsistema GPIO del RK3588 y la diferencia entre polling activo e interrupciones por software.

**Archivos de código:** `01_gpio_salida.py` · `02_gpio_entrada.py`

---

## 5.1 Fundamentos de GPIO

### ¿Qué es GPIO?

GPIO (General Purpose Input/Output) son pines del SoC que el software puede configurar dinámicamente como entradas o salidas digitales. Un pin configurado como salida puede estar en dos estados: alto (típicamente 3.3 V en el RK3588) o bajo (0 V). Un pin configurado como entrada puede leer el nivel de tensión que le aplica un circuito externo.

### Organización de los GPIO del RK3588

El RK3588 organiza sus pines GPIO en bancos numerados del 0 al 5. Cada banco gestiona hasta 32 líneas agrupadas en cuatro grupos de 8 bits: A (bits 0–7), B (bits 8–15), C (bits 16–23) y D (bits 24–31).

La **fórmula de numeración global** permite calcular el offset de cualquier línea:

```
offset = banco × 32 + (letra − A) × 8 + bit

Ejemplos:
  GPIO3_A1  →  3 × 32 + 0 × 8 + 1  =  97   (pin físico 12)
  GPIO3_A4  →  3 × 32 + 0 × 8 + 4  = 100   (pin físico 13)
  GPIO4_B2  →  4 × 32 + 1 × 8 + 2  = 138
```

### El subsistema GPIO Character Device

El kernel Linux expone cada banco como un character device en `/dev/gpiochipN`. Las operaciones se realizan mediante llamadas `ioctl()`:

| Llamada ioctl | Función |
|---|---|
| `GPIO_V2_GET_LINEINFO_IOCTL` | Consultar estado y configuración de una línea |
| `GPIO_V2_GET_LINE_IOCTL` | Solicitar una o más líneas con configuración |
| `GPIO_V2_LINE_SET_VALUES_IOCTL` | Escribir valores de salida |
| `GPIO_V2_LINE_GET_VALUES_IOCTL` | Leer valores de entrada |

La biblioteca **libgpiod v2** encapsula estas llamadas y proporciona una API segura en Python, sin requerir privilegios root.

### ¿Por qué no usar wiringpi o RPi.GPIO?

Estas bibliotecas acceden directamente a `/dev/mem` (el mapa completo de memoria física). Dar acceso a `/dev/mem` sin root equivale a dar acceso de lectura/escritura a toda la RAM y registros del SoC, lo cual es inaceptable desde el punto de vista de seguridad. libgpiod, en cambio, solo otorga acceso a las líneas GPIO explícitamente solicitadas.

---

## 5.2 Módulo 1: control de salida digital

**Archivo:** `01_gpio_salida.py`  
**Hardware:** LED + resistencia 330 Ω conectados al pin físico 12 (GPIO3_A1)

### El circuito

```
Pin físico 12 (3.3V alto) ──┤ 330 Ω ├──┤ LED ├──── Pin físico 6 (GND)
```

**Cálculo de la resistencia:** Con V_alto = 3.3 V y V_f ≈ 2.0 V (LED rojo):

```
I = (V_alto - V_f) / R = (3.3 - 2.0) / 330 = 3.9 mA
```

Esto está muy por debajo del máximo de corriente por pin del RK3588 (12 mA), garantizando operación segura.

### El código explicado

```python
import gpiod
from gpiod.line import Direction, Value

CHIP  = "/dev/gpiochip3"   # banco GPIO3
LINEA = 1                   # GPIO3_A1: offset 1 dentro del banco 3

with gpiod.request_lines(
    CHIP,
    consumer="gpio-salida",
    config={LINEA: gpiod.LineSettings(direction=Direction.OUTPUT)},
) as solicitud:
    solicitud.set_value(LINEA, Value.ACTIVE)   # pin en ALTO: LED enciende
    solicitud.set_value(LINEA, Value.INACTIVE) # pin en BAJO: LED apaga
```

**`request_lines()` como gestor de contexto:**  
El bloque `with` garantiza que las líneas se liberan automáticamente al salir, incluso si ocurre una excepción. Esto evita que otros programas queden bloqueados esperando acceso a la misma línea.

**`Direction.OUTPUT` vs `Direction.INPUT`:**  
- `OUTPUT`: el SoC controla activamente el nivel de tensión del pin
- `INPUT`: el SoC lee el nivel de tensión que impone el circuito externo

**`Value.ACTIVE` vs `Value.INACTIVE`:**  
Son independientes de la polaridad física. Si el pin tiene polaridad activa-baja configurada, `ACTIVE` produciría nivel bajo. Para este ejemplo, la polaridad por defecto es activa-alta: `ACTIVE` = 3.3 V.

### Ejecución

```bash
python3 01_gpio_salida.py
```

**Salida esperada:**
```
Línea GPIO3_A1 adquirida en modo salida.
Presione Ctrl+C para terminar.

Ciclo 0001 — ALTO  (3.3 V)
Ciclo 0001 — BAJO  (0 V)
Ciclo 0002 — ALTO  (3.3 V)
...
```

---

## 5.3 Módulo 2: lectura de entrada con detección de flancos

**Archivo:** `02_gpio_entrada.py`  
**Hardware:** Pulsador conectado entre el pin físico 13 (GPIO3_A4) y GND

### Polling activo vs detección de flancos

**Polling activo:**
```python
while True:
    nivel = solicitud.get_value(LINEA)   # consulta continua
    if nivel == Value.INACTIVE:
        print("pulsador presionado")
    time.sleep(0.01)  # 100 Hz de muestreo
```

Problema: el proceso consume CPU de forma continua (≈ 10–100% de un núcleo) incluso cuando no pasa nada. En un sistema multitarea esto penaliza a otros procesos.

**Detección de flancos (este módulo):**
```python
for evento in solicitud.read_edge_events():   # bloqueante
    print("evento detectado")
```

`read_edge_events()` suspende el proceso hasta que el hardware detecta una transición. El planificador del kernel puede asignar ese núcleo a otras tareas mientras tanto. El costo de CPU en espera es ~0%.

### Rebote mecánico (bouncing)

Los pulsadores mecánicos no hacen un único cambio de nivel al presionarse: las láminas metálicas rebotan varias veces produciendo múltiples transiciones en un período de 1–20 ms. Sin filtrado, un único clic físico genera 5–20 eventos de software.

libgpiod v2 incorpora filtrado de rebote en el kernel mediante `debounce_period`. El kernel descarta transiciones más cortas que el período especificado.

### El código explicado

```python
import datetime
import gpiod
from gpiod.line import Bias, Direction, Edge

configuracion = gpiod.LineSettings(
    direction=Direction.INPUT,
    bias=Bias.PULL_UP,
    edge_detection=Edge.BOTH,
    debounce_period=datetime.timedelta(milliseconds=5),
)
```

**`Bias.PULL_UP`:** Conecta internamente la línea a 3.3 V a través de una resistencia de pull-up. En reposo (pulsador abierto), la línea lee alto. Al presionar (pulsador conecta a GND), la línea lee bajo. Sin pull-up, el pin quedaría "flotando" con nivel indefinido.

**`Edge.BOTH`:** Detectar tanto flancos de subida (BAJO→ALTO) como de bajada (ALTO→BAJO). Para detectar solo la pulsación inicial usar `Edge.FALLING`.

### Ejecución y salida esperada

```bash
python3 02_gpio_entrada.py
```

```
  [   23.842100 s]  Flanco de BAJADA  → pulsador presionado
  [   24.301547 s]  Flanco de SUBIDA  → pulsador soltado
```

---

## 5.4 Herramientas de línea de comandos (gpiod)

Para explorar el hardware sin escribir Python:

```bash
# Listar todos los bancos GPIO del sistema
gpiodetect

# Ver el estado de todas las líneas del banco 3
gpioinfo /dev/gpiochip3

# Leer el nivel actual de la línea 1 del banco 3
gpioget /dev/gpiochip3 1

# Poner la línea en estado alto durante 2 segundos
gpioset --toggle 2000ms /dev/gpiochip3 1=1

# Esperar un evento de flanco en la línea 4
gpiomon --num-events 5 /dev/gpiochip3 4
```

---

## 5.5 Lectura simultánea de múltiples líneas

libgpiod permite solicitar varias líneas en una sola llamada, lo que garantiza que se leen en el mismo instante:

```python
import gpiod
from gpiod.line import Direction

CHIP   = "/dev/gpiochip3"
LINEAS = {1: gpiod.LineSettings(direction=Direction.INPUT),
          4: gpiod.LineSettings(direction=Direction.INPUT),
          5: gpiod.LineSettings(direction=Direction.INPUT)}

with gpiod.request_lines(CHIP, consumer="multi-lectura", config=LINEAS) as req:
    valores = req.get_values([1, 4, 5])
    print(f"GPIO3_A1={valores[0]}  GPIO3_A4={valores[1]}  GPIO3_A5={valores[2]}")
```

---

## Resumen del capítulo

- El RK3588 organiza los GPIO en bancos de 32 líneas cada uno, identificados por la fórmula `banco × 32 + grupo × 8 + bit`.
- libgpiod v2 proporciona acceso seguro sin root mediante el character device `/dev/gpiochipN`.
- La detección de flancos con `read_edge_events()` es más eficiente que el polling activo porque no consume CPU mientras espera.
- El filtrado de rebote por tiempo (`debounce_period`) previene múltiples eventos por una sola pulsación mecánica.

## Ejercicios

1. Modifique `01_gpio_salida.py` para que el LED parpadee siguiendo el patrón Morse de las letras "SOS" (··· — — — ···).
2. Combine los módulos 1 y 2: cuando se presione el pulsador, el LED cambie de estado (toggle). Requiere gestionar el estado actual del LED dentro del bucle de eventos.
3. Conecte tres LEDs a los pines físicos 11, 12 y 15. Modifique `01_gpio_salida.py` para encenderlos en secuencia (efecto "perseguidor") usando la lectura simultánea de múltiples líneas del apartado 5.5.
