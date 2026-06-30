# Capítulo 1 — Presentando la Orange Pi 5 Plus

## Objetivo

Al finalizar este capítulo el lector será capaz de describir la arquitectura del SoC RK3588, identificar cada componente del hardware en la placa, interpretar el diagrama de pines del cabecero de 40 pines y posicionar la Orange Pi 5 Plus en el ecosistema de placas de desarrollo de alto rendimiento.

---

## 1.1 ¿Qué es una placa de desarrollo de un solo tablero (SBC)?

Una SBC (Single Board Computer) es una computadora completa integrada en una sola placa de circuito impreso. A diferencia de un microcontrolador (como Arduino), una SBC ejecuta un sistema operativo completo (Linux, Android) y dispone de procesador de aplicaciones, memoria RAM, almacenamiento, interfaces de red y conectores de E/S en un único dispositivo.

La Orange Pi 5 Plus pertenece a la categoría de SBC de alto rendimiento: su potencia de cómputo es comparable a la de un computador de escritorio de gama baja de 2020, con la particularidad de incluir hardware especializado para inteligencia artificial (NPU) y procesamiento multimedia (VPU).

---

## 1.2 El SoC Rockchip RK3588: arquitectura interna

El componente central de la placa es el SoC (System on Chip) **Rockchip RK3588**, fabricado con proceso de 8 nm. Un SoC integra en un único die de silicio todos los subsistemas que en una computadora convencional ocuparían múltiples chips:

```
┌─────────────────────────────────────────────────────────┐
│                     RK3588  (8 nm)                      │
│                                                         │
│  ┌─────────────────┐    ┌────────────────────────────┐  │
│  │   CPU big.LITTLE │    │          GPU               │  │
│  │  4× Cortex-A76  │    │   Mali-G610 MP4            │  │
│  │  (2.4 GHz)      │    │   OpenGL ES 3.1            │  │
│  │  4× Cortex-A55  │    │   OpenGL 3.0               │  │
│  │  (1.8 GHz)      │    │   (driver Panfrost)        │  │
│  └─────────────────┘    └────────────────────────────┘  │
│                                                         │
│  ┌─────────────────┐    ┌────────────────────────────┐  │
│  │      NPU        │    │          VPU               │  │
│  │  3× 2 TOPS      │    │  H.265/H.264/AV1           │  │
│  │  = 6 TOPS INT8  │    │  8K@60fps decode           │  │
│  │  (driver rknpu) │    │  (driver rkmpp)            │  │
│  └─────────────────┘    └────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Controladores de bus: I2C · SPI · UART · USB · PCIe ││
│  │  GPIO · PWM · I2S (audio) · MIPI CSI/DSI            ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### CPU: arquitectura big.LITTLE

La CPU implementa la topología **DynamIQ** de ARM, con dos clústeres de diferente perfil de rendimiento:

- **Clúster "big"**: 4× Cortex-A76 a 2.4 GHz. Diseñados para cargas de trabajo intensivas: compilación, inferencia en CPU, servidores web.
- **Clúster "LITTLE"**: 4× Cortex-A55 a 1.8 GHz. Optimizados para eficiencia energética: tareas de fondo, espera de E/S, operaciones livianas.

El planificador del kernel Linux asigna dinámicamente cada tarea al clúster más apropiado según la carga y la política de energía activa. El resultado práctico: alto rendimiento cuando se necesita, bajo consumo cuando no.

### GPU: Mali-G610 MP4

La GPU implementa la arquitectura **Valhall** de ARM. En Linux, el driver de código abierto **Panfrost** (incluido en el kernel mainline desde 5.2) expone las siguientes APIs:

| API | Versión | Uso típico |
|---|---|---|
| OpenGL ES | 3.1 | Gráficos móviles, OpenCV DNN |
| OpenGL | 3.0 | Aplicaciones de escritorio, glmark2 |
| Vulkan | Experimental | Renderizado moderno de alto rendimiento |

### NPU: 6 TOPS

La NPU (Neural Processing Unit) consta de **tres núcleos independientes de 2 TOPS** cada uno, para un rendimiento combinado de 6 TOPS (tera-operaciones por segundo con enteros de 8 bits, INT8). Está diseñada para ejecutar inferencia de redes neuronales convolucionales hasta 90× más rápido que la CPU.

El stack de software se denomina **RKNN** y se compone de:
- `rknn-toolkit2` (PC): convierte modelos de PyTorch/TensorFlow/ONNX al formato `.rknn`
- `rknn-toolkit-lite2` (placa): ejecuta inferencia en la NPU

### VPU: decodificación de video por hardware

La VPU (Video Processing Unit) decodifica video en hardware sin ocupar la CPU:

| Formato | Resolución máxima |
|---|---|
| H.265 (HEVC) | 8K @ 60 fps |
| H.264 (AVC) | 8K @ 30 fps |
| AV1 | 8K @ 24 fps |
| VP9 | 8K @ 60 fps |

---

## 1.3 Especificaciones completas de la placa

| Componente | Especificación |
|---|---|
| **SoC** | Rockchip RK3588 (8 nm) |
| **CPU** | 4× Cortex-A76 @ 2.4 GHz + 4× Cortex-A55 @ 1.8 GHz |
| **RAM** | 4 / 8 / 16 GB LPDDR4X (según variante) |
| **GPU** | Mali-G610 MP4 |
| **NPU** | 6 TOPS (3 núcleos × 2 TOPS, INT8) |
| **Almacenamiento** | MicroSD · eMMC · M.2 NVMe (PCIe 3.0 ×4) |
| **Ethernet** | 2× 2.5 GbE (Realtek RTL8125BG) |
| **WiFi** | IEEE 802.11 a/b/g/n/ac (AP6275P) |
| **Bluetooth** | 5.0 |
| **USB** | 2× USB 3.0 + 2× USB 2.0 + 1× USB-C (OTG/DP) |
| **Video salida** | HDMI 2.1 (8K@60fps) + DisplayPort 1.4 (vía USB-C) + MIPI DSI |
| **Video entrada** | 2× MIPI CSI (cámara) |
| **Audio** | Jack 3.5 mm (entrada/salida) + HDMI |
| **GPIO** | Cabecero de 40 pines (compatible con Raspberry Pi) |
| **Alimentación** | USB-C PD (12V/2A recomendado) |
| **Dimensiones** | 100 × 75 mm |

---

## 1.4 Comparativa en el mercado

La Orange Pi 5 Plus compite directamente con otras SBC de alto rendimiento basadas en ARM. La siguiente tabla compara las cuatro plataformas más relevantes al momento de escribir este capítulo:

| Característica | Orange Pi 5 Plus | Raspberry Pi 5 | Radxa ROCK 5B | Banana Pi M7 |
|---|---|---|---|---|
| SoC | RK3588 | BCM2712 | RK3588 | RK3588 |
| CPU (big) | 4× A76 @ 2.4G | 4× A76 @ 2.4G | 4× A76 @ 2.4G | 4× A76 @ 2.4G |
| RAM máx. | 16 GB | 8 GB | 16 GB | 16 GB |
| NPU | 6 TOPS | ❌ | 6 TOPS | 6 TOPS |
| Ethernet | 2× 2.5 GbE | 1× GbE | 1× 2.5 GbE | 2× 2.5 GbE |
| M.2 NVMe | ✓ (PCIe 3.0) | ✓ (PCIe 2.0) | ✓ (PCIe 3.0) | ✓ (PCIe 3.0) |
| Soporte HW accel. | RKNN | VideoCore VII | RKNN | RKNN |
| Madurez del ecosistema | Media | Alta | Media | Baja |
| Disponibilidad | Alta | Alta | Media | Baja |

**¿Cuándo elegir la Orange Pi 5 Plus?**
- Proyectos que requieren inferencia de IA en el borde (edge AI) a bajo costo
- Aplicaciones de red que aprovechan los dos puertos 2.5 GbE
- Servidores de medios o NAS con decodificación 8K por hardware
- Plataforma de desarrollo cuando se necesita mayor RAM que la Raspberry Pi 5

**¿Cuándo preferir la Raspberry Pi 5?**
- Cuando la prioridad es la madurez del ecosistema y la documentación abundante
- Proyectos educativos donde la comunidad de soporte es crítica
- Si la NPU no es un requisito

---

## 1.5 Diagrama del cabecero de 40 pines

El cabecero de 40 pines mantiene compatibilidad de pinout con la Raspberry Pi, lo que permite reutilizar la mayoría de HATs y módulos de expansión del ecosistema.

```
       3.3V  (1) (2)  5V
 I2C2_SDA   (3) (4)  5V
 I2C2_SCL   (5) (6)  GND
 PWM14      (7) (8)  UART2_TX
 GND        (9)(10)  UART2_RX
 GPIO3_A3  (11)(12)  GPIO3_A1  ← LED (Módulo 1)
 GPIO3_A4  (13)(14)  GND       ← Botón (Módulo 2)
 GPIO3_A5  (15)(16)  GPIO3_A6
 3.3V      (17)(18)  GPIO3_A7
 SPI0_MOSI (19)(20)  GND
 SPI0_MISO (21)(22)  GPIO3_B0
 SPI0_SCLK (23)(24)  SPI0_CS0
 GND       (25)(26)  SPI0_CS1
 GPIO4_D1  (27)(28)  GPIO4_D2
 GPIO4_D4  (29)(30)  GND
 GPIO4_D5  (31)(32)  GPIO3_C0
 GPIO3_B2  (33)(34)  GND
 GPIO3_B3  (35)(36)  GPIO3_B4
 GPIO3_B6  (37)(38)  GPIO3_B5
 GND       (39)(40)  GPIO3_B7
```

Pines de mayor interés para los capítulos siguientes:

| Pin físico | Función | Capítulo |
|---|---|---|
| 1, 17 | 3.3 V (alimentación sensores) | 5, 6 |
| 2, 4 | 5 V (alimentación servo) | 6 |
| 6, 9, 14… | GND | todos |
| 3, 5 | SDA/SCL del bus I2C-2 | 6 |
| 7 | PWM14 (señal servo) | 6 |
| 12 | GPIO3_A1 (LED de prueba) | 5 |
| 13 | GPIO3_A4 (pulsador) | 5 |
| 19, 21, 23, 24 | Bus SPI-0 | 6 |

---

## 1.6 El kernel BSP: por qué importa

La imagen oficial de Orange Pi utiliza un kernel **BSP** (Board Support Package) mantenido por Rockchip en la rama `5.10.x`. Este kernel incluye:

- Drivers propietarios para la NPU (`rknpu`) y la VPU (`rkmpp`)
- Soporte completo para todos los periféricos del RK3588
- 41 paquetes del sistema retenidos con `apt-mark hold` para evitar que actualizaciones del repositorio Ubuntu rompan los componentes vendor

El kernel mainline de kernel.org (≥ 6.x) tiene soporte parcial y creciente para el RK3588, pero sin los drivers propietarios de NPU/VPU. Para proyectos que no requieren estas aceleraciones, el mainline ofrece ciclos de actualización de seguridad más frecuentes.

---

## Resumen del capítulo

- La Orange Pi 5 Plus es una SBC basada en el SoC RK3588 con CPU big.LITTLE de 8 núcleos, GPU Mali-G610, NPU de 6 TOPS y VPU de decodificación 8K.
- El RK3588 integra en un único chip todos los subsistemas necesarios para una computadora completa.
- Frente a la Raspberry Pi 5, su ventaja principal es la NPU de 6 TOPS y los dos puertos Ethernet de 2.5 GbE; su desventaja es un ecosistema menos maduro.
- El cabecero de 40 pines expone GPIO, I2C, SPI, UART y PWM, con compatibilidad de pinout con Raspberry Pi.

## Ejercicios

1. Identifique en el diagrama de pines cuáles son los pines de SDA y SCL del bus I2C-2. ¿Qué voltaje de señal usan?
2. Calcule cuántas operaciones de multiplicación-acumulación puede realizar la NPU en 1 segundo si corre a capacidad máxima y las operaciones son INT8.
3. Compare los anchos de banda teóricos de PCIe 3.0 ×4 (para NVMe) con la velocidad máxima de las interfaces Ethernet 2.5 GbE. ¿Cuál es el cuello de botella para un servidor NAS?
