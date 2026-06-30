# Capítulo 9 — Creando tu Propio Sistema con Buildroot

## Objetivo

Al finalizar este capítulo el lector comprenderá por qué y cuándo crear un sistema Linux mínimo personalizado, configurará Buildroot para el RK3588 y generará una imagen de sistema completamente funcional y de tamaño reducido.

---

## 9.1 ¿Por qué crear un sistema mínimo?

La imagen oficial de Ubuntu para la Orange Pi 5 Plus ocupa ~4 GB en la microSD. Incluye decenas de servicios (impresoras, Bluetooth, avahi, cups, etc.), bibliotecas de escritorio y herramientas de desarrollo que no tienen utilidad en un dispositivo embebido final.

Un sistema construido con Buildroot puede arrancar en menos de 3 segundos, ocupar menos de 50 MB y contener exactamente y solo lo necesario para la aplicación.

**Casos de uso típicos de Buildroot:**
- Dispositivo IoT con aplicación Python y acceso a GPIO, sin escritorio
- Gateway industrial con comunicación serial + red, sin herramientas de usuario
- Sistema de cámara: captura + inferencia NPU + transmisión de red
- Appliance de red: dos puertos 2.5 GbE + servidor web mínimo

---

## 9.2 Buildroot: arquitectura y conceptos

Buildroot es un sistema de construcción que automatiza:
1. La descarga de código fuente de todos los componentes
2. La compilación cruzada de cada componente para el target (ARM64)
3. El ensamblado del sistema de archivos raíz (rootfs)
4. La generación de la imagen de disco final

```
Buildroot
├── toolchain/          → Configuración de la toolchain
├── arch/               → Configuraciones por arquitectura
├── board/              → Configuraciones específicas de placa
├── package/            → ~2500 paquetes disponibles
│   ├── python3/
│   ├── gpiod/
│   ├── openssh/
│   └── ...
├── configs/            → Configuraciones guardadas (defconfig)
├── output/
│   ├── build/          → Código fuente compilado
│   ├── host/           → Toolchain generada
│   ├── target/         → Sistema de archivos del dispositivo
│   └── images/         → Imagen de disco final
└── .config             → Configuración actual
```

---

## 9.3 Instalación de Buildroot

```bash
# En el PC de desarrollo (Ubuntu 22.04)
sudo apt install wget make gcc g++ unzip rsync bc cpio \
    python3 libncurses-dev libssl-dev

# Descargar la versión estable más reciente de Buildroot
wget https://buildroot.org/downloads/buildroot-2024.02.tar.gz
tar xzf buildroot-2024.02.tar.gz
cd buildroot-2024.02
```

---

## 9.4 Configuración para la Orange Pi 5 Plus

Buildroot no incluye una defconfig para la Orange Pi 5 Plus en su árbol principal, pero podemos basarnos en la configuración genérica de RK3588 o crear la nuestra.

### Crear la configuración desde cero

```bash
# Iniciar con una configuración vacía
make menuconfig
```

En el menú interactivo, configurar:

```
Target options
  → Target Architecture: AArch64 (little endian)
  → Target Architecture Variant: cortex-A55 (compatible con todos los núcleos)

Toolchain
  → Toolchain type: External toolchain
  → Toolchain: Bootlin toolchains
  → Toolchain origin: Toollin
  → Toolchain: aarch64 gcc 13.x glibc 2.36

System configuration
  → System hostname: orangepi5plus
  → System banner: Orange Pi 5 Plus - Custom Build
  → Root password: (establecer una contraseña)
  → /dev management: Dynamic using devtmpfs + mdev

Kernel
  → Linux kernel: yes
  → Kernel version: Custom version
  → URL: https://github.com/orangepi-xunlong/linux-orangepi/archive/orange-pi-5.10-rk3588.tar.gz
  → Kernel configuration: Using a custom config file
  → Config file path: board/orangepi5plus/linux.config

Target packages
  → Networking applications
      → dropbear (servidor SSH minimalista)
  → Hardware handling
      → gpiod
      → i2c-tools
  → Interpreter languages
      → Python 3
          → python-pip
          → python-smbus2 (si está disponible)
  → Shell and utilities
      → bash
      → htop
```

### Guardar la configuración

```bash
make savedefconfig DEFCONFIG=configs/orangepi5plus_defconfig
```

---

## 9.5 Personalizar el rootfs

Buildroot permite agregar archivos personalizados al rootfs antes de generar la imagen:

```bash
mkdir -p board/orangepi5plus/rootfs-overlay/etc/init.d/
mkdir -p board/orangepi5plus/rootfs-overlay/home/pi/scripts/
```

**Script de inicio personalizado** (`board/orangepi5plus/rootfs-overlay/etc/init.d/S99aplicacion`):

```bash
#!/bin/sh

case "$1" in
    start)
        echo "Iniciando aplicación principal..."
        python3 /home/pi/scripts/main.py &
        ;;
    stop)
        echo "Deteniendo aplicación..."
        pkill -f main.py
        ;;
esac
```

En `menuconfig`, habilitar:
```
System configuration
  → Root filesystem overlay directories: board/orangepi5plus/rootfs-overlay
```

---

## 9.6 Compilar y generar la imagen

```bash
# Compilar todo (primera vez: 30–90 minutos según la red y el PC)
make -j$(nproc)

# Las imágenes resultantes estarán en:
ls -lh output/images/
# sdcard.img   → imagen lista para grabar en microSD
# rootfs.ext4  → sistema de archivos raíz
# Image        → kernel
```

### Grabar en microSD

```bash
sudo dd if=output/images/sdcard.img of=/dev/sdX bs=4M status=progress conv=fsync
```

---

## 9.7 Compilaciones incrementales

```bash
# Recompilar solo un paquete
make python3-rebuild

# Agregar un nuevo paquete
make menuconfig   # activar el paquete
make             # Buildroot solo compilará lo nuevo

# Limpiar una compilación parcial
make clean       # elimina output/build/ pero conserva la toolchain
make distclean   # elimina todo output/ (incluye la toolchain)
```

---

## 9.8 Comparativa: imagen oficial vs. Buildroot

| Característica | Ubuntu oficial | Buildroot |
|---|---|---|
| Tamaño en disco | ~4 GB | 30–100 MB |
| Tiempo de arranque | 15–25 s | 2–5 s |
| RAM en reposo | ~300 MB | 20–60 MB |
| Paquetes disponibles | 50.000+ (APT) | ~2.500 |
| Facilidad de uso | Alta | Media |
| Reproducibilidad | Baja | Alta (100%) |
| Soporte NPU/VPU | Completo | Requiere integración manual |
| Uso recomendado | Desarrollo, prototipado | Producción, dispositivos finales |

---

## Resumen del capítulo

- Buildroot genera sistemas Linux mínimos reproducibles, ideales para dispositivos finales embebidos.
- El proceso de configuración, compilación y grabación produce una imagen completamente personalizada para el RK3588.
- La ventaja principal sobre Ubuntu es el control total sobre qué software incluye el sistema y el arranque significativamente más rápido.
- La integración de drivers propietarios (NPU, VPU) en Buildroot requiere pasos adicionales de integración manual.

## Ejercicios

1. Genere una imagen Buildroot con Python 3, gpiod y dropbear (SSH). Mida el tamaño de la imagen resultante y el tiempo de arranque hasta tener acceso SSH.
2. Agregue un overlay al rootfs que instale el script `07_leds_integrados.py` en `/home/root/` y lo ejecute automáticamente al arrancar via `S99leds`.
3. Compare el consumo de RAM en reposo entre la imagen Ubuntu oficial y la imagen Buildroot usando `free -h`. ¿Cuánta RAM ahorra el sistema mínimo?
