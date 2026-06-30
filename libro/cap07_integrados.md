# Capítulo 7 — Los Componentes Integrados de la Placa

## Objetivo

Al finalizar este capítulo el lector controlará los LEDs integrados de la placa mediante el subsistema LED del kernel, leerá la temperatura de los núcleos CPU desde los sensores integrados y comprenderá el sistema de gestión térmica del RK3588.

**Archivos de código:** `07_leds_integrados.py`

---

## 7.1 Subsistema LED del kernel Linux

### Arquitectura

El subsistema LED de Linux (`drivers/leds/`) implementa una capa de abstracción entre los drivers de hardware (LEDs conectados a GPIO, PWM o I2C) y las políticas de control. Expone cada LED como un conjunto de archivos en `/sys/class/leds/<nombre>/`:

```
/sys/class/leds/<nombre>/
    brightness        → nivel de brillo actual (escritura/lectura)
    max_brightness    → valor máximo soportado (solo lectura)
    trigger           → modo de control activo (escritura/lectura)
```

### Triggers: control autónomo por el kernel

Un trigger es un módulo del kernel que controla el LED de forma autónoma. Al escribir el nombre de un trigger en el archivo `trigger`, el kernel toma el control del LED sin necesidad de intervención del espacio de usuario.

```bash
# Ver triggers disponibles y el activo (entre corchetes)
cat /sys/class/leds/green_led/trigger
# Ejemplo: none rc-feedback ... [heartbeat] timer mmc0 phy0tx cpu0 ...
```

**Triggers disponibles en la imagen Orange Pi:**

| Trigger | Comportamiento |
|---|---|
| `none` | Control manual desde espacio de usuario |
| `heartbeat` | Parpadeo con patrón cardíaco proporcional a la carga del CPU |
| `timer` | Parpadeo a frecuencia fija (configurable con `delay_on`/`delay_off`) |
| `mmc0` | Actividad de la tarjeta microSD |
| `phy0tx` | Actividad de transmisión WiFi |
| `cpu0`–`cpu7` | Actividad de cada núcleo CPU |
| `default-on` | Encendido permanente |

### LEDs integrados de la Orange Pi 5 Plus

La placa tiene dos LEDs soldados directamente sobre el PCB:

| Nombre | Color | Función por defecto |
|---|---|---|
| `green_led` | Verde | Trigger `heartbeat` (carga del sistema) |
| `blue_led` | Azul | Trigger `heartbeat` |

---

## 7.2 Módulo 7: control de LEDs integrados

**Archivo:** `07_leds_integrados.py`

### Control manual

Para controlar un LED manualmente, primero hay que cambiar el trigger a `none`:

```python
# Ceder el control al proceso actual
with open("/sys/class/leds/green_led/trigger", "w") as f:
    f.write("none")

# Encender
with open("/sys/class/leds/green_led/brightness", "w") as f:
    f.write("1")

# Apagar
with open("/sys/class/leds/green_led/brightness", "w") as f:
    f.write("0")

# Restaurar el modo automático
with open("/sys/class/leds/green_led/trigger", "w") as f:
    f.write("heartbeat")
```

### Leer el trigger activo

El archivo `trigger` muestra todos los triggers disponibles con el activo entre corchetes:

```
none rc-feedback [heartbeat] timer default-on ...
```

Para extraer el activo:

```python
def leer_trigger_activo(led):
    contenido = open(f"/sys/class/leds/{led}/trigger").read()
    for token in contenido.split():
        if token.startswith("[") and token.endswith("]"):
            return token[1:-1]
    return "desconocido"
```

### Ejecución

```bash
python3 07_leds_integrados.py
```

```
Adquiriendo control manual de los LEDs integrados...
  green_led: 'heartbeat' → 'none' (control manual)
  blue_led: 'heartbeat' → 'none' (control manual)

Control adquirido. Iniciando secuencia (Ctrl+C para salir).

  green_led: ENCENDIDO
  green_led: APAGADO
  blue_led: ENCENDIDO
  ...
```

### Control desde la línea de comandos

```bash
# Modo timer: parpadeo a 5 Hz (100 ms encendido, 100 ms apagado)
echo "timer" | sudo tee /sys/class/leds/green_led/trigger
echo "100"   | sudo tee /sys/class/leds/green_led/delay_on
echo "100"   | sudo tee /sys/class/leds/green_led/delay_off

# LED vinculado a la actividad de la tarjeta SD
echo "mmc0"  | sudo tee /sys/class/leds/blue_led/trigger

# Restaurar
echo "heartbeat" | sudo tee /sys/class/leds/green_led/trigger
```

---

## 7.3 Gestión térmica del RK3588

### Zonas térmicas

El RK3588 incluye múltiples sensores de temperatura integrados en el die de silicio. El kernel los expone en `/sys/class/thermal/`:

```bash
for z in /sys/class/thermal/thermal_zone*/; do
    tipo=$(cat "$z/type")
    temp=$(( $(cat "$z/temp") / 1000 ))
    printf "%-30s %d°C\n" "$tipo" "$temp"
done
```

**Zonas típicas:**

| Zona | Descripción | Temperatura operativa normal |
|---|---|---|
| `soc-thermal` | Temperatura media del SoC | 45–65°C |
| `bigcore0-thermal` | Clúster A76 núcleos 0-1 | 50–70°C |
| `bigcore1-thermal` | Clúster A76 núcleos 2-3 | 50–70°C |
| `littlecore-thermal` | Clúster A55 | 45–60°C |
| `gpu-thermal` | GPU Mali-G610 | 45–65°C |
| `npu-thermal` | NPU | 50–70°C |

### Política de control térmico (thermal throttling)

Cuando la temperatura supera umbrales configurados, el kernel reduce automáticamente las frecuencias para evitar daños:

```bash
# Ver los umbrales de la zona del SoC
cat /sys/class/thermal/thermal_zone0/trip_point_*/temp
# Típicamente: 70°C (passive), 85°C (hot), 95°C (critical)
```

- **Passive (70°C):** el kernel reduce la frecuencia máxima de la CPU
- **Hot (85°C):** reducción más agresiva
- **Critical (95°C):** apagado inmediato del sistema para proteger el hardware

### Política de frecuencia (governor)

```bash
# Ver el governor activo para todos los núcleos
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Cambiar a modo performance (sin reducción de frecuencia)
echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Volver a schedutil (recomendado para uso general)
echo "schedutil" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Ver frecuencias disponibles
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies
```

### Script de monitoreo integrado

```python
"""
Monitor en tiempo real: temperatura de todas las zonas + frecuencia CPU.
Sin dependencias externas.
"""
import os
import time

def leer_zonas():
    base = "/sys/class/thermal"
    zonas = []
    for entrada in sorted(os.listdir(base)):
        if not entrada.startswith("thermal_zone"):
            continue
        ruta = f"{base}/{entrada}"
        try:
            tipo = open(f"{ruta}/type").read().strip()
            temp = int(open(f"{ruta}/temp").read().strip()) // 1000
            zonas.append((tipo, temp))
        except OSError:
            pass
    return zonas

def leer_frecuencias():
    freqs = []
    for i in range(8):
        try:
            ruta = f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq"
            freq_khz = int(open(ruta).read().strip())
            freqs.append(freq_khz // 1000)
        except OSError:
            freqs.append(0)
    return freqs

try:
    while True:
        zonas = leer_zonas()
        freqs = leer_frecuencias()

        print(f"\n{'─'*55}")
        print(f"{'Zona térmica':<28} {'Temp':>6}")
        for tipo, temp in zonas:
            alerta = " ⚠" if temp > 80 else ""
            print(f"  {tipo:<26} {temp:>4}°C{alerta}")

        print(f"\n{'CPU':>4}  " + "  ".join(f"A76" if i >= 4 else "A55" for i in range(8)))
        print(f"{'MHz':>4}  " + "  ".join(f"{f:4d}" for f in freqs))
        time.sleep(2)

except KeyboardInterrupt:
    print("\nMonitor detenido.")
```

---

## Resumen del capítulo

- Los LEDs integrados de la Orange Pi 5 Plus (`green_led`, `blue_led`) se controlan a través de `/sys/class/leds/` mediante el subsistema LED del kernel.
- Los triggers permiten que el kernel controle los LEDs de forma autónoma (heartbeat, timer, mmc0) sin intervención del espacio de usuario.
- El RK3588 incluye sensores de temperatura integrados en el die, accesibles en `/sys/class/thermal/`.
- El thermal throttling reduce automáticamente las frecuencias para proteger el hardware cuando la temperatura supera los umbrales configurados.

## Ejercicios

1. Modifique `07_leds_integrados.py` para que el LED verde parpadee rápido cuando la temperatura del SoC supere 70°C, y lento cuando esté por debajo. Use el trigger `timer` con `delay_on` y `delay_off` configurables.
2. Combine el monitoreo de temperatura con el control de LED: cree un script que encienda el LED azul permanentemente si la CPU supera 75°C, y lo apague cuando baje de 65°C (control con histéresis).
3. Investigue el archivo `/sys/class/thermal/thermal_zone0/thermal_cooling_device0/cur_state`. ¿Qué representa? ¿Cómo se relaciona con el thermal throttling?
