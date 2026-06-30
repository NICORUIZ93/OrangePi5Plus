# Orange Pi 5 Plus — RK3588

**OS:** Ubuntu 22.04.5 LTS · **Kernel:** 5.10.110-rockchip-rk3588 (vendor BSP)

| Componente | Detalle |
|---|---|
| CPU | 4× Cortex-A76 @ 2.4GHz + 4× Cortex-A55 @ 1.8GHz |
| RAM | 16 GB LPDDR4X |
| GPU | Mali-G610 MP4 — OpenGL 3.0 / OpenGL ES 3.1 (Panfrost) |
| NPU | 6 TOPS (3× 2T, RKNPU) |
| Ethernet | 2× 2.5GbE RTL8125BG |
| WiFi | 802.11 a/b/g/n/ac (AP6275P) |
| GPIO | 40 pines (pinout compatible RPi) |

---

## Setup inicial (una vez, requiere sudo)

```bash
./setup_gpio_permissions.sh   # grupos i2c/spi/gpio, udev, overlay PWM, servicio systemd
./setup_npu.sh                # instala rknn-toolkit-lite2 y librknnrt.so
sudo reboot
```

Después del reinicio todo funciona sin `sudo`.

---

## Scripts de ejemplo

| Script | Hardware | Notas |
|---|---|---|
| `Led_test_blink.py` | GPIO — pin físico 12 (GPIO3_A1) | usa `gpiod`, no `wiringpi` |
| `servo_test.py` | PWM — pin físico 7 (PWM14) | sysfs `/sys/class/pwm/pwmchip2` |
| `i2c_scan.py` | I2C bus 2 (pines 3/5) | escanea 0x03–0x77 |
| `OLED_SSD1306.py` | I2C — pantalla SSD1306 0x3C | requiere `luma.oled` |
| `spi_loopback_test.py` | SPI0 — `/dev/spidev0.0` | puentea MOSI(19)↔MISO(21) para loopback |
| `leds_onboard.py` | LEDs soldados `green_led`/`blue_led` | vía `/sys/class/leds/` |
| `npu_inference_example.py` | NPU — ResNet-18 | descarga modelo y foto automáticamente |

---

## Problemas conocidos

### 1. `pwm0-m0` no funciona

El overlay `pwm0-m0` (activo por defecto) comparte pin con `feaa0000.i2c`, que lo reclama primero. Resultado: `I/O error` al escribir en `enable`. El pin de PWM del cabecero (físico 7) usa `pwm14-m0` → `pwmchip2`. `setup_gpio_permissions.sh` corrige `/boot/orangepiEnv.txt`.

```bash
# Verificar qué pwmchip corresponde a qué driver tras el reboot:
cat /sys/class/pwm/pwmchip*/device/uevent | grep -B1 DRIVER
```

### 2. NPU reporta errores en dmesg pero funciona

```
RKNPU: can't request region for resource
failed to initialize power model
```

Bug del kernel vendor (inofensivo). La inferencia funciona con normalidad.

### 3. `wiringpi` requiere root permanentemente

Accede a `/dev/mem` (memoria física cruda). No hay workaround seguro. Usar `gpiod` para GPIO digital y sysfs para PWM.

### 4. `spidev.xfer2()` modifica la lista de entrada in-place

```python
# MAL — enviado queda sobreescrito, la comparación es trivialmente True
recibido = spi.xfer2(enviado)

# BIEN
recibido = spi.xfer2(list(enviado))
```
