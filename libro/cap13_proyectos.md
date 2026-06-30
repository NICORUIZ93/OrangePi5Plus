# Capítulo 13 — Proyectos Integradores

## Objetivo

Al finalizar este capítulo el lector habrá integrado los conocimientos de todos los capítulos anteriores en tres proyectos funcionales completos, capaces de ejecutarse de forma autónoma como servicios del sistema.

---

## Proyecto 1 — Estación Meteorológica IoT

### Descripción

Una estación meteorológica autónoma que lee temperatura y humedad desde un sensor I2C, publica los datos a un broker MQTT cada 30 segundos, muestra el estado en el display OLED integrado y envía alertas cuando la temperatura supera un umbral configurable.

### Hardware requerido

- Sensor BME280 (temperatura, humedad, presión) — I2C, bus 2, dirección 0x76
- Display OLED SSD1306 — I2C, bus 2, dirección 0x3C
- LED indicador en GPIO3_A1 (pin 12)

### Arquitectura del sistema

```
BME280 (I2C) ────→ lector_sensor.py ────→ MQTT broker (local)
                         │
                         └──→ OLED display
                         └──→ LED parpadeo (heartbeat)
                         └──→ log del sistema (journald)

MQTT broker ←──── cualquier cliente (Node-RED, Grafana, etc.)
```

### Implementación

```python
#!/usr/bin/env python3
"""
estacion_meteorologica.py

Estación meteorológica autónoma para Orange Pi 5 Plus.
Prerrequisitos: pip install smbus2 luma.oled paho-mqtt bme280
                sudo systemctl start mosquitto
"""

import os
import time
import json
import logging
import signal
from datetime import datetime

import smbus2
import bme280
import paho.mqtt.client as mqtt
import gpiod
from luma.core.interface.serial import i2c
from luma.devices import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# Configuración
MQTT_HOST      = "localhost"
MQTT_PORT      = 1883
MQTT_TOPIC     = "estacion/exterior"
INTERVALO_S    = 30
ALERTA_TEMP    = 35.0    # °C
I2C_BUS        = 2
BME280_ADDR    = 0x76
OLED_ADDR      = 0x3C
GPIO_CHIP      = "/dev/gpiochip3"
GPIO_LED       = 1       # GPIO3_A1

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("estacion")

ejecutando = True

def manejador_senal(sig, frame):
    global ejecutando
    ejecutando = False

signal.signal(signal.SIGTERM, manejador_senal)
signal.signal(signal.SIGINT,  manejador_senal)


def iniciar_bme280():
    bus = smbus2.SMBus(I2C_BUS)
    parametros = bme280.load_calibration_params(bus, BME280_ADDR)
    return bus, parametros


def leer_sensor(bus, parametros):
    datos = bme280.sample(bus, BME280_ADDR, parametros)
    return {
        "temperatura": round(datos.temperature, 2),
        "humedad":     round(datos.humidity, 2),
        "presion":     round(datos.pressure, 2),
        "timestamp":   datetime.now().isoformat(),
    }


def actualizar_oled(dispositivo, datos):
    with canvas(dispositivo) as ctx:
        ctx.text((0, 0),  "Estacion Meteo",          fill="white")
        ctx.text((0, 16), f"T: {datos['temperatura']}°C", fill="white")
        ctx.text((0, 28), f"H: {datos['humedad']}%",    fill="white")
        ctx.text((0, 40), f"P: {datos['presion']} hPa", fill="white")


def main():
    # Inicializar sensor
    bus, parametros = iniciar_bme280()
    log.info("BME280 inicializado en I2C-%d addr=0x%02X", I2C_BUS, BME280_ADDR)

    # Inicializar OLED
    serial = i2c(port=I2C_BUS, address=OLED_ADDR)
    oled   = ssd1306(serial)

    # Inicializar LED
    chip   = gpiod.Chip(GPIO_CHIP)
    lineas = chip.request_lines(
        {GPIO_LED: gpiod.LineSettings(direction=gpiod.Direction.OUTPUT)},
        consumer="estacion"
    )

    # Inicializar MQTT
    cliente_mqtt = mqtt.Client()
    cliente_mqtt.connect(MQTT_HOST, MQTT_PORT, 60)
    cliente_mqtt.loop_start()
    log.info("MQTT conectado a %s:%d", MQTT_HOST, MQTT_PORT)

    try:
        while ejecutando:
            datos = leer_sensor(bus, parametros)
            log.info("T=%.2f°C H=%.2f%% P=%.2f hPa",
                     datos["temperatura"], datos["humedad"], datos["presion"])

            # Publicar por MQTT
            cliente_mqtt.publish(MQTT_TOPIC, json.dumps(datos))

            # Actualizar pantalla
            actualizar_oled(oled, datos)

            # LED de alerta si temperatura alta
            estado_led = gpiod.Value.ACTIVE \
                if datos["temperatura"] > ALERTA_TEMP else gpiod.Value.INACTIVE
            lineas.set_value(GPIO_LED, estado_led)

            time.sleep(INTERVALO_S)

    finally:
        cliente_mqtt.loop_stop()
        cliente_mqtt.disconnect()
        lineas.set_value(GPIO_LED, gpiod.Value.INACTIVE)
        lineas.release()
        oled.cleanup()
        bus.close()
        log.info("Estación detenida correctamente")


if __name__ == "__main__":
    main()
```

### Servicio systemd

```ini
# /etc/systemd/system/estacion-meteo.service
[Unit]
Description=Estación Meteorológica IoT
After=network.target mosquitto.service

[Service]
Type=simple
User=orangepi
WorkingDirectory=/home/orangepi/proyectos
ExecStart=/home/orangepi/proyectos/venv/bin/python3 estacion_meteorologica.py
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

---

## Proyecto 2 — Sistema de Reconocimiento Facial

### Descripción

Un sistema de control de acceso que captura imágenes desde una cámara USB, detecta y reconoce rostros usando la NPU del RK3588, y controla un servomotor (puerta) vía PWM. Los eventos se registran con timestamp en un archivo de log.

### Hardware requerido

- Cámara USB compatible V4L2 (cualquier webcam)
- Servomotor SG90 conectado a pwmchip2/pwm0 (overlay `pwm14-m0`)
- LED rojo en GPIO3_A1 — acceso denegado
- LED verde en GPIO3_A4 — acceso concedido

### Flujo del sistema

```
Cámara USB (V4L2)
        ↓
  cv2.VideoCapture(0)
        ↓
  Detección de rostro (Haar Cascade — CPU)
        ↓ (si hay rostro)
  Recortar y normalizar región de interés
        ↓
  Inferencia NPU (MobileNetV2 fine-tuned)
        ↓
  Comparar embedding con base de datos
        ↓
  ┌─────────────┬───────────────┐
  ↓             ↓               ↓
Desconocido  Persona A      Persona B
LED rojo     LED verde       LED verde
Servo 0°     Servo 90°       Servo 90°
Log: DENY    Log: GRANT      Log: GRANT
```

### Implementación: detector de rostros

```python
#!/usr/bin/env python3
"""
control_acceso.py — Sistema de control de acceso con reconocimiento facial.
Prerrequisitos: pip install opencv-python numpy
                rknn-toolkit-lite2 instalado
                ./setup_npu.sh ejecutado
"""

import os
import cv2
import numpy as np
import time
import logging
from pathlib import Path
from datetime import datetime

os.environ.setdefault("RKNN_LOG_LEVEL", "0")
from rknnlite.api import RKNNLite

import gpiod

# Configuración
MODELO_RKNN    = "facenet_rk3588.rknn"
CARA_CASCADA   = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
UMBRAL_SIMILITUD = 0.75
GPIO_CHIP      = "/dev/gpiochip3"
LED_ROJO       = 1    # GPIO3_A1 — acceso denegado
LED_VERDE      = 4    # GPIO3_A4 — acceso concedido
LOG_ARCHIVO    = "/var/log/control_acceso.log"

logging.basicConfig(
    filename=LOG_ARCHIVO,
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

def similitud_coseno(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def extraer_embedding(rknn, cara_img):
    cara_rgb = cv2.cvtColor(cara_img, cv2.COLOR_BGR2RGB)
    cara_224 = cv2.resize(cara_rgb, (160, 160))
    tensor   = np.expand_dims(cara_224, axis=0)
    salida   = rknn.inference(inputs=[tensor])
    return salida[0][0] / np.linalg.norm(salida[0][0])


def controlar_servo(angulo_grados):
    # 0° = 500 µs, 90° = 1500 µs, 180° = 2500 µs
    periodo_ns    = 20_000_000
    duty_ns       = int(500_000 + angulo_grados * (2_000_000 / 180))

    PWM_DIR = Path("/sys/class/pwm/pwmchip2/pwm0")
    (PWM_DIR / "period"    ).write_text(str(periodo_ns))
    (PWM_DIR / "duty_cycle").write_text(str(duty_ns))
    (PWM_DIR / "enable"    ).write_text("1")


def main():
    # Cargar detector de caras
    detector = cv2.CascadeClassifier(CARA_CASCADA)

    # Cargar embeddings conocidos (base de datos)
    base_datos = {}
    for archivo in Path("embeddings/").glob("*.npy"):
        nombre = archivo.stem
        base_datos[nombre] = np.load(archivo)
    print(f"Base de datos: {len(base_datos)} persona(s) registrada(s)")

    # Inicializar NPU
    rknn = RKNNLite()
    if rknn.load_rknn(MODELO_RKNN) != 0:
        raise RuntimeError("No se pudo cargar el modelo RKNN")
    if rknn.init_runtime() != 0:
        raise RuntimeError("No se pudo inicializar el runtime NPU")

    # Inicializar GPIO
    chip   = gpiod.Chip(GPIO_CHIP)
    lineas = chip.request_lines(
        {
            LED_ROJO:  gpiod.LineSettings(direction=gpiod.Direction.OUTPUT),
            LED_VERDE: gpiod.LineSettings(direction=gpiod.Direction.OUTPUT),
        },
        consumer="acceso"
    )

    # Abrir cámara
    cam = cv2.VideoCapture(0)

    try:
        while True:
            ret, frame = cam.read()
            if not ret:
                break

            gris  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            caras = detector.detectMultiScale(gris, 1.1, 4, minSize=(100, 100))

            for (x, y, w, h) in caras:
                cara_recortada = frame[y:y+h, x:x+w]
                embedding      = extraer_embedding(rknn, cara_recortada)

                # Buscar la persona más similar en la base de datos
                mejor_nombre = None
                mejor_sim    = 0.0
                for nombre, emb_conocido in base_datos.items():
                    sim = similitud_coseno(embedding, emb_conocido)
                    if sim > mejor_sim:
                        mejor_sim    = sim
                        mejor_nombre = nombre

                if mejor_sim >= UMBRAL_SIMILITUD:
                    logging.info("ACCESO CONCEDIDO: %s (sim=%.3f)", mejor_nombre, mejor_sim)
                    controlar_servo(90)
                    lineas.set_values({LED_VERDE: gpiod.Value.ACTIVE,
                                       LED_ROJO:  gpiod.Value.INACTIVE})
                    time.sleep(3)
                    controlar_servo(0)
                else:
                    logging.info("ACCESO DENEGADO (mejor sim=%.3f)", mejor_sim)
                    lineas.set_values({LED_ROJO:  gpiod.Value.ACTIVE,
                                       LED_VERDE: gpiod.Value.INACTIVE})
                    time.sleep(1)

                lineas.set_values({LED_ROJO:  gpiod.Value.INACTIVE,
                                   LED_VERDE: gpiod.Value.INACTIVE})

            time.sleep(0.1)

    finally:
        cam.release()
        lineas.release()
        rknn.release()


if __name__ == "__main__":
    main()
```

---

## Proyecto 3 — NAS / Router con dos puertos 2.5 GbE

### Descripción

La Orange Pi 5 Plus incluye dos interfaces de red 2.5 GbE (RTL8125BG). Este proyecto convierte la placa en un router doméstico con firewall, servidor de archivos (Samba) y monitoreo de red, aprovechando ambas interfaces.

### Arquitectura de red

```
Internet (WAN)
      │
  eth1 (RTL8125BG)
      │
  Orange Pi 5 Plus
  ┌───────────────┐
  │  nftables     │  ← firewall + NAT
  │  dnsmasq      │  ← DHCP + DNS
  │  hostapd      │  ← WiFi AP (si hay adaptador USB)
  │  samba        │  ← servidor de archivos
  └───────────────┘
      │
  eth0 (RTL8125BG)
      │
   Switch LAN
   └── PC, Smart TV, etc.
```

### Configuración de red

```bash
# /etc/network/interfaces
auto eth1
iface eth1 inet dhcp          # WAN: obtiene IP del ISP

auto eth0
iface eth0 inet static
    address 192.168.10.1
    netmask 255.255.255.0     # LAN: IP fija para la placa
```

### Firewall con nftables

```bash
# /etc/nftables.conf
table inet filtro {
    chain entrada {
        type filter hook input priority 0; policy drop;

        # Permitir conexiones establecidas
        ct state established,related accept

        # Permitir todo desde LAN
        iifname "eth0" accept

        # Permitir SSH desde WAN (solo para administración)
        iifname "eth1" tcp dport 22 accept

        # Rechazar el resto
        log prefix "bloqueado: "
    }

    chain reenvio {
        type filter hook forward priority 0; policy drop;
        iifname "eth0" oifname "eth1" ct state new accept
        ct state established,related accept
    }

    chain salida {
        type filter hook output priority 0; policy accept;
    }
}

# NAT: enmascarar tráfico LAN con la IP WAN
table ip nat {
    chain postrouting {
        type nat hook postrouting priority 100;
        oifname "eth1" masquerade
    }
}
```

```bash
# Habilitar enrutamiento IP en el kernel
echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-router.conf
sudo sysctl -p /etc/sysctl.d/99-router.conf

# Aplicar el firewall
sudo nft -f /etc/nftables.conf
sudo systemctl enable nftables
```

### Servidor DHCP y DNS (dnsmasq)

```ini
# /etc/dnsmasq.conf
interface=eth0
dhcp-range=192.168.10.100,192.168.10.200,24h
dhcp-option=3,192.168.10.1     # gateway = la placa
dhcp-option=6,192.168.10.1     # DNS = la placa
```

### Servidor de archivos Samba

```bash
sudo apt install samba

# /etc/samba/smb.conf
[compartido]
    path = /media/disco_usb
    valid users = orangepi
    read only = no
    browsable = yes
    create mask = 0664
    directory mask = 0775
```

### Monitor de tráfico en Python

```python
#!/usr/bin/env python3
"""
monitor_red.py — Monitoreo de tráfico en los dos puertos 2.5GbE.
"""

import time

def leer_estadisticas(interfaz):
    base = f"/sys/class/net/{interfaz}/statistics/"
    rx = int(open(base + "rx_bytes").read())
    tx = int(open(base + "tx_bytes").read())
    return rx, tx

def velocidad_mbps(bytes_delta, intervalo_s):
    return (bytes_delta * 8) / (intervalo_s * 1_000_000)

def main():
    interfaces = ["eth0", "eth1"]
    anterior = {iface: leer_estadisticas(iface) for iface in interfaces}
    intervalo = 1.0

    print(f"{'Interfaz':<8} {'RX (Mbps)':>10} {'TX (Mbps)':>10}")
    print("-" * 32)

    while True:
        time.sleep(intervalo)
        for iface in interfaces:
            actual = leer_estadisticas(iface)
            rx_vel = velocidad_mbps(actual[0] - anterior[iface][0], intervalo)
            tx_vel = velocidad_mbps(actual[1] - anterior[iface][1], intervalo)
            print(f"\r{iface:<8} {rx_vel:>10.2f} {tx_vel:>10.2f}", end="  ", flush=True)
            anterior[iface] = actual
        print()

if __name__ == "__main__":
    main()
```

---

## Integración de los tres proyectos

Los tres proyectos son independientes pero demuestran la versatilidad de la plataforma:

| Proyecto | Subsistemas usados | Capítulos relevantes |
|---|---|---|
| Estación Meteorológica | I2C, OLED, GPIO, systemd | 6, 7, 10 |
| Reconocimiento Facial | NPU, PWM, GPIO, V4L2 | 6, 7, 12 |
| NAS/Router | Red 2.5GbE, systemd, sysfs | 3, 10 |

### Árbol de dependencias de conocimiento

```
Cap 1 (Hardware) ─→ Cap 2 (OS) ─→ Cap 3 (Linux) ─→ Cap 4 (Python)
                                                          │
                    ┌─────────────────────────────────────┤
                    ↓             ↓                       ↓
               Cap 5 (GPIO)   Cap 6 (I2C/SPI)       Cap 7 (LEDs/Thermal)
                    │             │
                    └──────┬──────┘
                           ↓
                      Cap 10 (C/Daemons)
                           │
               ┌───────────┼───────────┐
               ↓           ↓           ↓
          Cap 8 (Boot)  Cap 9 (BR)  Cap 11 (Drivers)
                                         │
                                    Cap 12 (NPU)
                                         │
                                    Cap 13 (Proyectos)
```

---

## Ejercicios finales

1. **Proyecto Estación Meteorológica**: Extienda el sistema para publicar datos históricos en una base de datos SQLite local. Añada un endpoint HTTP con el módulo `http.server` de Python que devuelva el último registro en formato JSON.

2. **Proyecto Reconocimiento Facial**: Implemente la fase de registro. Cree un script `registrar_persona.py` que captura 10 fotos de la persona, calcula el embedding promedio y lo guarda en `embeddings/<nombre>.npy`.

3. **Proyecto NAS/Router**: Mida el throughput máximo del router con `iperf3`: un PC conectado en LAN y otro como cliente externo. ¿Cuánto CPU consume el enrutamiento a 2.5 Gbps? ¿Es suficiente la CPU del RK3588 para saturar los dos puertos?

4. **Integración**: Combine los proyectos 1 y 2. Cuando el sistema de reconocimiento facial conceda acceso, publique un evento MQTT al broker de la estación meteorológica con el nombre de la persona y la temperatura actual. Visualice ambos flujos de datos en un dashboard de Node-RED.
