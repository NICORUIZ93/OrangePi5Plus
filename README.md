# Orange Pi 5 Plus

Scripts y notas de hardware para la Orange Pi 5 Plus (RK3588) corriendo Ubuntu 22.04
(kernel vendor `5.10.110-rockchip-rk3588`, imagen oficial Orange Pi).

## Problemas conocidos de esta imagen y cómo se resolvieron

Por defecto, en esta imagen **nada de GPIO/I2C/SPI/PWM funciona sin `sudo`**, y el
overlay de PWM que viene activado por defecto **no funciona en absoluto** (choca con
un bus I2C interno). Esto no es obvio por los mensajes de error, así que se documenta
aquí para no perder horas re-descubriéndolo.

### 1. I2C/SPI/GPIO/LEDs piden sudo siempre

Causa: el usuario no pertenece a los grupos dueños de `/dev/i2c-*`, no existe el grupo
`spi`, y `/dev/gpiochip*` es `root:root`. Las librerías legacy tipo `wiringpi` además
acceden directo a `/dev/mem` (memoria física cruda), por lo que **nunca** pueden
funcionar sin root sin comprometer la seguridad del sistema completo (dar acceso a
`/dev/mem` a un grupo equivale a dar acceso de lectura/escritura a toda la RAM).

Solución: en vez de wiringpi, usar la interfaz moderna del kernel —
`/dev/gpiochip*` vía [libgpiod](https://libgpiod.readthedocs.io/) para GPIO digital,
y `/sys/class/pwm/` para PWM real por hardware. Estas sí se pueden compartir con un
grupo de forma segura (solo dan acceso a líneas GPIO o canales PWM puntuales, no a
memoria arbitraria).

Ejecuta una vez:

```bash
./setup_gpio_permissions.sh
sudo reboot
```

Esto crea los grupos `i2c`, `spi`, `gpio`, las reglas udev necesarias, corrige el
overlay de PWM (ver punto 2) y agrega tu usuario a esos grupos. Después del reinicio,
I2C, SPI, GPIO y los LEDs onboard funcionan **sin sudo**.

### 2. El overlay de PWM por defecto (`pwm0-m0`) no sirve

`pwm0-m0` controla el pin `fd8b0000.pwm`, que en esta placa está físicamente
compartido con un controlador I2C interno (`feaa0000.i2c`) que lo reclama primero.
Intentar habilitarlo da `rockchip-pinctrl: pin gpio0-15 already requested` en
`dmesg` y un error de I/O al escribir en `enable`.

El pin de PWM realmente disponible en el header de 40 pines (pin físico 7,
etiquetado "PWM14" en `gpio readall`) usa el overlay **`pwm14-m0`**, que expone un
`pwmchip` nuevo (en esta imagen, `pwmchip2`). `setup_gpio_permissions.sh` ya hace
este cambio en `/boot/orangepiEnv.txt`.

Si tu imagen difiere y `pwmchip2` no es el correcto, identifica el tuyo con:

```bash
cat /sys/class/pwm/pwmchip*/device/uevent | grep -B1 DRIVER
```

### 3. El NPU (6 TOPS) parece roto en `dmesg` pero en realidad funciona

Al arrancar aparecen errores como `RKNPU: can't request region for resource` y
`failed to initialize power model`. **Esto es ruido inofensivo** — es un bug conocido
del kernel vendor ([reportado aquí](https://github.com/orangepi-xunlong/linux-orangepi/issues/88))
que no impide que el NPU funcione. Se confirmó con una inferencia real (ResNet-18,
predicción correcta) usando `setup_npu.sh`.

```bash
./setup_npu.sh
```

Instala `rknn-toolkit-lite2` (Python) y `librknnrt.so` descargando solo los archivos
puntuales necesarios del repo oficial `airockchip/rknn-toolkit2` (el repo completo
pesa ~3.8GB, por eso no se clona).

## Scripts de ejemplo (hardware real, probados)

| Script | Qué hace | Pin/bus |
|---|---|---|
| `Led_test_blink.py` | Parpadea un LED vía GPIO digital (`gpiod`) | Pin físico 12 (GPIO3_A1) |
| `servo_test.py` | Mueve un servo por ancho de pulso (PWM real, 50Hz) | Pin físico 7 (PWM14) |
| `OLED_SSD1306.py` | Dibuja una onda senoidal animada en una pantalla SSD1306 (I2C, vía `luma.oled`) | I2C bus 2, dirección 0x3C |
| `ssd1306.py` + `fontawesome.py` | Driver SSD1306 manual alternativo (sin `luma`), con set de iconos | I2C |

Todos corren **sin sudo** después de ejecutar `setup_gpio_permissions.sh` una vez y
reiniciar.

## Setup scripts

- `setup_gpio_permissions.sh` — grupos + udev + overlay PWM + servicio systemd, para
  usar GPIO/PWM/I2C/SPI/LEDs sin sudo. Idempotente, se puede correr varias veces.
- `setup_npu.sh` — instala el runtime y toolkit del NPU (RK3588/RKNN).
