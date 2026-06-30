# Orange Pi 5 Plus — Desarrollo de sistemas embebidos con Linux

**Plataforma:** Orange Pi 5 Plus · **SoC:** Rockchip RK3588  
**Sistema operativo:** Ubuntu 22.04.5 LTS · **Kernel:** 5.10.110-rockchip-rk3588 (BSP Rockchip)

## Descripción del proyecto

Este repositorio contiene una serie de módulos de código y documentación técnica para la enseñanza de programación de hardware en sistemas embebidos Linux. Los módulos cubren los principales subsistemas de E/S del SoC RK3588: GPIO, PWM, I2C, SPI, el subsistema LED del kernel y la unidad de procesamiento neuronal (NPU).

Cada módulo Python incluye la fundamentación teórica del subsistema correspondiente, la especificación de las conexiones de hardware y el código documentado. La guía `TUTORIAL.md` desarrolla en detalle la teoría y los procedimientos de cada módulo.

## Especificaciones del hardware

| Componente | Especificación |
|---|---|
| SoC | Rockchip RK3588 |
| CPU | 4× Cortex-A76 @ 2.4 GHz + 4× Cortex-A55 @ 1.8 GHz |
| RAM | 16 GB LPDDR4X |
| GPU | Mali-G610 MP4 — OpenGL ES 3.1 / OpenGL 3.0 (driver Panfrost) |
| NPU | 6 TOPS — 3 núcleos × 2 TOPS (driver RKNPU) |
| Ethernet | 2× 2.5 GbE (Realtek RTL8125BG) |
| WiFi | IEEE 802.11 a/b/g/n/ac (AP6275P) |
| GPIO | Cabecero de 40 pines (pinout compatible con Raspberry Pi) |

## Configuración inicial del sistema

Los siguientes scripts configuran el sistema operativo para el acceso a los periféricos sin privilegios de superusuario. Se ejecutan una única vez tras la instalación del sistema operativo.

```bash
./setup_gpio_permissions.sh   # Grupos, reglas udev, overlay PWM, servicio systemd
./setup_npu.sh                # Runtime RKNN (rknn-toolkit-lite2 + librknnrt.so)
sudo reboot
```

Tras el reinicio, todos los módulos de este repositorio funcionan sin `sudo`.

## Dependencias Python

```bash
pip3 install gpiod smbus2 spidev luma.oled opencv-python numpy
```

## Estructura del repositorio

| Archivo | Subsistema | Descripción |
|---|---|---|
| `setup_gpio_permissions.sh` | Sistema | Permisos de GPIO, I2C, SPI, PWM y LEDs |
| `setup_npu.sh` | Sistema | Instalación del runtime RKNN |
| `01_gpio_salida.py` | GPIO | Control de salida digital mediante libgpiod v2 |
| `02_gpio_entrada.py` | GPIO | Lectura de entrada digital con detección de flancos |
| `03_pwm_servo.py` | PWM | Control de servomotor mediante PWM por hardware |
| `04_i2c_escaneo.py` | I2C | Enumeración de dispositivos en el bus I2C |
| `05_i2c_oled.py` | I2C | Control de pantalla OLED SSD1306 (128×64) |
| `06_spi_loopback.py` | SPI | Verificación del bus SPI mediante loopback |
| `07_leds_integrados.py` | LED | Control de LEDs de la placa mediante sysfs |
| `08_npu_inferencia.py` | NPU | Clasificación de imágenes con ResNet-18 en el NPU |
| `TUTORIAL.md` | Documentación | Guía académica completa con teoría y procedimientos |

## Problemas conocidos del BSP

| Síntoma | Causa raíz | Solución |
|---|---|---|
| `I/O error` al escribir en `/sys/class/pwm/pwmchip0/export` | El overlay `pwm0-m0` comparte el pin GPIO0_15 con `feaa0000.i2c`, que lo reclama durante el arranque | `setup_gpio_permissions.sh` cambia el overlay a `pwm14-m0` |
| Mensajes `RKNPU: can't request region` en dmesg | Defecto del árbol BSP 5.10 | Sin impacto funcional; el NPU opera correctamente |
| Acceso denegado a `/dev/gpiochipN`, `/dev/i2c-*`, `/dev/spidev*` | El usuario no pertenece a los grupos `gpio`, `i2c` y `spi` | `setup_gpio_permissions.sh` |
