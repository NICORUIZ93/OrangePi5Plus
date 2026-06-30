# Capítulo 8 — Compilación Cruzada y el Bootloader

## Objetivo

Al finalizar este capítulo el lector entenderá el proceso de arranque del RK3588 desde la BootROM hasta el kernel, compilará U-Boot desde el código fuente y generará una imagen de kernel Linux personalizada mediante compilación cruzada en un PC x86-64.

---

## 8.1 ¿Qué es la compilación cruzada?

Una **toolchain** es el conjunto de herramientas necesarias para compilar código: compilador, enlazador, bibliotecas estándar y utilidades. En desarrollo nativo, la toolchain genera código para la misma arquitectura donde se ejecuta (x86-64 → x86-64).

En **compilación cruzada**, la toolchain genera código para una arquitectura diferente:

```
PC de desarrollo (x86-64)  →  [toolchain aarch64-linux-gnu]  →  binario para ARM64
```

**¿Por qué no compilar directamente en la placa?**

Compilar el kernel completo en la Orange Pi 5 Plus tarda aproximadamente 90 minutos. En un PC moderno con 16 núcleos, el mismo proceso tarda 10–15 minutos. Para ciclos de desarrollo iterativos, la compilación cruzada es prácticamente obligatoria.

---

## 8.2 Instalar la toolchain de compilación cruzada

```bash
# En el PC de desarrollo (Ubuntu 22.04 x86-64)
sudo apt install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu

# Verificar
aarch64-linux-gnu-gcc --version
# aarch64-linux-gnu-gcc (Ubuntu 11.3.0-1ubuntu1~22.04) 11.3.0
```

Variables de entorno para compilación cruzada:

```bash
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
```

---

## 8.3 El proceso de arranque del RK3588

El arranque del RK3588 sigue una cadena de confianza de cuatro etapas:

```
┌──────────────────────────────────────────────────────────────┐
│ ETAPA 1: BootROM (ROM interna del chip, inmutable)           │
│  - Código grabado en ROM de fábrica, no modificable          │
│  - Inicializa la DRAM en modo básico                         │
│  - Busca el siguiente cargador en: SPI NOR, eMMC, SD, USB   │
└───────────────────────┬──────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│ ETAPA 2: SPL / TPL (Secondary/Tertiary Program Loader)       │
│  - Pequeños binarios (~30 KB) que caben en la SRAM interna   │
│  - Inicializa DRAM, configura DDR PHY                        │
│  - Carga U-Boot proper desde almacenamiento                  │
└───────────────────────┬──────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│ ETAPA 3: U-Boot                                              │
│  - Bootloader de propósito general                           │
│  - Inicializa periféricos: USB, Ethernet, MMC, HDMI          │
│  - Lee /boot/orangepiEnv.txt para parámetros del kernel      │
│  - Carga el kernel y el Device Tree Blob                     │
│  - Transfiere el control al kernel                           │
└───────────────────────┬──────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│ ETAPA 4: Kernel Linux                                        │
│  - Inicializa los drivers de todos los periféricos           │
│  - Monta el sistema de archivos raíz                         │
│  - Lanza el proceso init (systemd)                           │
└──────────────────────────────────────────────────────────────┘
```

### /boot/orangepiEnv.txt

Este archivo es el punto de configuración del bootloader accesible desde el usuario. U-Boot lo lee en cada arranque:

```bash
cat /boot/orangepiEnv.txt
```

```
verbosity=1
bootlogo=false
overlay_prefix=rockchip
fdtfile=rockchip/rk3588-orangepi-5-plus.dtb
overlays=i2c2-m0 pwm14-m0 spi0-m2-cs0-cs1-spidev
extraargs=
```

| Parámetro | Descripción |
|---|---|
| `fdtfile` | Archivo Device Tree Blob para esta placa |
| `overlays` | Overlays de DT activos (periféricos a habilitar) |
| `extraargs` | Parámetros extra pasados al kernel |

---

## 8.4 Compilar U-Boot para el RK3588

```bash
# En el PC de desarrollo
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-

# Clonar el U-Boot de Rockchip
git clone --depth=1 https://github.com/rockchip-linux/u-boot.git
cd u-boot

# Aplicar la configuración para Orange Pi 5 Plus
make orangepi-5-plus-rk3588_defconfig

# Compilar (omite el binario final, necesita el ATF y DDR blobs de Rockchip)
make -j$(nproc)
```

> **Nota:** la imagen de U-Boot completa requiere binarios propietarios de Rockchip (ATF = Arm Trusted Firmware + blobs DDR PHY). La imagen oficial de Orange Pi los incluye precompilados. Para proyectos de producción, estos binarios deben obtenerse de los repositorios de Rockchip con registro previo.

---

## 8.5 Compilar el kernel Linux para el RK3588

```bash
# Clonar el kernel BSP de Orange Pi (rama para RK3588)
git clone --depth=1 -b orange-pi-5.10-rk3588 \
    https://github.com/orangepi-xunlong/linux-orangepi.git
cd linux-orangepi

# Aplicar la configuración por defecto para RK3588
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- rockchip_linux_defconfig

# Abrir el menú de configuración (opcional, para modificaciones)
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- menuconfig

# Compilar kernel + módulos + Device Tree Blobs
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc) \
    Image modules dtbs

# Los archivos compilados están en:
# arch/arm64/boot/Image           ← kernel
# arch/arm64/boot/dts/rockchip/   ← DTBs
```

### Instalar el kernel compilado en la placa

```bash
# En el PC, copiar kernel y DTB a la placa por SCP
scp arch/arm64/boot/Image orangepi@192.168.1.105:/boot/
scp arch/arm64/boot/dts/rockchip/rk3588-orangepi-5-plus.dtb \
    orangepi@192.168.1.105:/boot/dtb/rockchip/

# En la placa, instalar módulos
sudo make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
     INSTALL_MOD_PATH=/tmp/modules modules_install
# Luego copiar /tmp/modules/lib/modules/<versión>/ a la placa
```

---

## 8.6 Device Tree: descripción del hardware en texto

El Device Tree (DT) es una estructura de datos que describe al kernel qué hardware existe en la placa: procesadores, buses, periféricos, interrupciones y rangos de memoria. A diferencia de los PCs x86 (que usan ACPI para autodescubrimiento), los SoC ARM no tienen bus de detección estándar, por lo que el DT es obligatorio.

### Formato DTS (Device Tree Source)

```dts
// Fragmento del DT de la Orange Pi 5 Plus
/ {
    model = "Orange Pi 5 Plus";
    compatible = "xunlong,orangepi-5-plus", "rockchip,rk3588";

    memory@0 {
        device_type = "memory";
        reg = <0x0 0x00000000 0x0 0x100000000>;  /* 4 GB */
    };
};

&i2c2 {
    status = "okay";
    clock-frequency = <400000>;   /* 400 kHz */

    bmp280: bmp280@76 {
        compatible = "bosch,bmp280";
        reg = <0x76>;
    };
};
```

### Compilar un DTS a DTB

```bash
# En el árbol del kernel
dtc -I dts -O dtb \
    arch/arm64/boot/dts/rockchip/rk3588-orangepi-5-plus.dts \
    -o rk3588-orangepi-5-plus.dtb
```

---

## Resumen del capítulo

- La compilación cruzada permite generar binarios para ARM64 desde un PC x86-64 más rápido.
- El proceso de arranque del RK3588 sigue cuatro etapas: BootROM → SPL/TPL → U-Boot → Kernel.
- `/boot/orangepiEnv.txt` es el punto de entrada para configurar overlays y parámetros del kernel sin recompilar.
- El Device Tree describe el hardware al kernel en formato texto (DTS) compilado a binario (DTB).

## Ejercicios

1. Revise el archivo `/boot/orangepiEnv.txt` en la placa. Agregue el parámetro `extraargs=loglevel=7` y reinicie. ¿Cómo cambia la salida de `dmesg`?
2. Descargue y compile el U-Boot para la placa siguiendo las instrucciones del apartado 8.4. ¿Cuánto tiempo tarda la compilación en el PC vs. el tiempo estimado en la placa?
3. Use `dtc -I dtb -O dts` para descompilar el DTB activo de la placa (`/boot/dtb/rockchip/rk3588-orangepi-5-plus.dtb`) y localice la sección que describe el bus I2C-2.
