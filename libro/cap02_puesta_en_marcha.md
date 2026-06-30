# Capítulo 2 — Puesta en Marcha y Primer Contacto

## Objetivo

Al finalizar este capítulo el lector tendrá el sistema operativo instalado y configurado, acceso remoto por SSH, y el sistema actualizado y listo para el desarrollo.

---

## 2.1 Elección del sistema operativo

La Orange Pi 5 Plus puede ejecutar varios sistemas operativos. La elección determina qué drivers están disponibles, la madurez de los paquetes y el nivel de soporte de la comunidad.

| Sistema operativo | Base | NPU/VPU | Recomendado para |
|---|---|---|---|
| **Ubuntu 22.04 (oficial OrangePi)** | Ubuntu 22.04 LTS | ✓ completo | Desarrollo general, IA, multimedia |
| Orange Pi OS (Droid) | Android 12 | ✓ completo | Multimedia y escritorio |
| Debian (oficial OrangePi) | Debian 11 | ✓ completo | Servidores, proyectos headless |
| Armbian | Debian/Ubuntu | Parcial | Usuarios avanzados, kernel mainline |
| buildroot personalizado | Mínimo | Configurable | Sistemas embebidos de producción |

**Recomendación para este libro:** Ubuntu 22.04 LTS (imagen oficial de Orange Pi). Ofrece el mejor equilibrio entre soporte de hardware completo (NPU, VPU, GPU) y familiaridad con el ecosistema Ubuntu/Debian.

> **Nota sobre los paquetes retenidos:** La imagen oficial retiene 41 paquetes con `apt-mark hold` para proteger los componentes vendor. Ejecutar `sudo apt-mark showhold` muestra la lista completa. No se deben liberar estos paquetes, ya que una actualización rompería los drivers de NPU, GPU y multimedia.

---

## 2.2 Descarga y grabación de la imagen

### 2.2.1 Descargar la imagen oficial

1. Visitar el sitio oficial de Orange Pi: `orangepi.org`
2. Navegar a: **Orange Pi 5 Plus → Downloads → Ubuntu**
3. Descargar la imagen `Orangepi5plus_X.X.X_ubuntu_jammy_desktop_linux5.10.110.img.xz` (o la versión `server` para uso headless)

### 2.2.2 Verificar la integridad

```bash
# En el PC de desarrollo (Linux/macOS)
sha256sum Orangepi5plus_*.img.xz
# Comparar con el hash publicado en la página de descarga
```

### 2.2.3 Grabar en microSD

**Herramienta recomendada: balenaEtcher** (multiplataforma, interfaz gráfica)

```
1. Abrir balenaEtcher
2. "Flash from file" → seleccionar el archivo .img.xz
3. "Select target" → seleccionar la microSD (≥ 16 GB, clase A2 recomendada)
4. "Flash!" → esperar a que termine (5–15 minutos según velocidad de la tarjeta)
```

**Alternativa por línea de comandos (Linux):**

```bash
# Identificar el dispositivo de la microSD
lsblk

# Grabar la imagen (reemplazar /dev/sdX por el dispositivo correcto)
xzcat Orangepi5plus_*.img.xz | sudo dd of=/dev/sdX bs=4M status=progress conv=fsync

# Verificar que terminó sin errores
echo $?   # debe imprimir 0
```

> ⚠️ **Precaución:** verificar dos veces que `/dev/sdX` es la microSD y no un disco interno. El comando `dd` sobreescribe el dispositivo destino sin confirmación.

### 2.2.4 Grabar en eMMC (alternativa a microSD)

Si la placa tiene módulo eMMC soldado, la imagen puede grabarse directamente desde el sistema Linux ya en ejecución:

```bash
# Desde un sistema Linux corriendo en la placa (microSD)
sudo dd if=Orangepi5plus_*.img of=/dev/mmcblk1 bs=4M status=progress conv=fsync
```

---

## 2.3 Primer arranque

### 2.3.1 Conexiones necesarias

Para el primer arranque se recomienda tener conectado:
- Fuente de alimentación USB-C (12V/2A mínimo; 5V/3A funciona pero limita el rendimiento)
- Cable HDMI a monitor (para ver el proceso de arranque)
- Teclado USB

### 2.3.2 Credenciales por defecto

| Campo | Valor |
|---|---|
| Usuario | `orangepi` |
| Contraseña | `orangepi` |
| Usuario root | `root` |
| Contraseña root | `orangepi` |

> **Acción inmediata:** cambiar la contraseña en el primer arranque:
> ```bash
> passwd orangepi
> ```

### 2.3.3 Expansión del sistema de archivos

La imagen grabada ocupa menos espacio que la tarjeta. En el primer arranque, el sistema expande automáticamente la partición para usar toda la tarjeta. Verificar:

```bash
df -h /
# Debe mostrar el tamaño total de la tarjeta, no el de la imagen (~5 GB)
```

Si no se expandió automáticamente:

```bash
sudo orangepi-config   # → System → Expand filesystem
# O manualmente:
sudo resize2fs /dev/mmcblk0p2
```

---

## 2.4 Configuración de red y acceso SSH

### 2.4.1 Conectar por cable Ethernet

```bash
# Ver interfaces de red y sus direcciones IP
ip addr show
# O con el comando clásico
ifconfig

# Verificar conectividad
ping -c 4 8.8.8.8
```

### 2.4.2 Conectar a WiFi por terminal

```bash
# Listar redes disponibles
nmcli dev wifi list

# Conectarse a una red
nmcli dev wifi connect "NombreDeRed" password "contraseña"

# Verificar estado
nmcli connection show --active
```

### 2.4.3 Habilitar y acceder por SSH

SSH está habilitado por defecto en la imagen oficial.

```bash
# En la placa: verificar que el servicio está activo
sudo systemctl status ssh

# En caso de que no esté activo
sudo systemctl enable --now ssh
```

**Desde el PC de desarrollo:**

```bash
# Obtener la IP de la placa primero
# En la placa:  ip addr show eth0 | grep "inet "
# Resultado ejemplo: 192.168.1.105

# Conectarse
ssh orangepi@192.168.1.105
```

**Configurar acceso sin contraseña (clave SSH):**

```bash
# En el PC de desarrollo: generar par de claves (si no existe)
ssh-keygen -t ed25519 -C "desarrollo-orangepi"

# Copiar la clave pública a la placa
ssh-copy-id orangepi@192.168.1.105

# A partir de ahora, no se pide contraseña
ssh orangepi@192.168.1.105
```

---

## 2.5 Actualización del sistema

La imagen oficial incluye paquetes de Ubuntu 22.04. Antes de actualizar, es fundamental entender los paquetes retenidos.

### 2.5.1 Verificar paquetes retenidos

```bash
apt-mark showhold
```

Estos 41 paquetes (ffmpeg, mesa, chromium, rknn, wiringpi, etc.) NO deben actualizarse. Contienen versiones parcheadas por Rockchip/Orange Pi que habilitan la aceleración de hardware.

### 2.5.2 Actualizar el sistema de forma segura

```bash
# Actualizar la lista de paquetes disponibles
sudo apt update

# Actualizar paquetes NO retenidos (seguro)
sudo apt upgrade

# Instalar actualizaciones de seguridad urgentes
sudo apt dist-upgrade --no-install-recommends
```

La opción `upgrade` (sin `full-upgrade` ni `dist-upgrade`) respeta los paquetes retenidos.

### 2.5.3 Instalar herramientas esenciales

```bash
sudo apt install -y \
    git \
    curl \
    wget \
    build-essential \
    python3-pip \
    python3-venv \
    htop \
    tree \
    vim \
    i2c-tools \
    gpiod
```

---

## 2.6 Monitoreo básico del sistema

### Temperatura de los núcleos CPU

```bash
cat /sys/class/thermal/thermal_zone*/temp
# Los valores están en milicélsius (68000 = 68°C)

# Script para mostrar todas las zonas térmicas con nombre
for zone in /sys/class/thermal/thermal_zone*/; do
    type=$(cat "$zone/type")
    temp=$(cat "$zone/temp")
    printf "%-30s %d°C\n" "$type" $((temp / 1000))
done
```

### Frecuencia actual de la CPU

```bash
grep "" /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
# Los núcleos A76 (cpu4-cpu7) mostrarán frecuencias más altas bajo carga
```

### Uso de CPU y RAM en tiempo real

```bash
htop   # Interfaz interactiva; q para salir
```

### Información del sistema

```bash
uname -a          # Versión del kernel
lscpu             # Detalles del procesador
free -h           # RAM disponible
lsblk             # Almacenamiento conectado
lsusb             # Dispositivos USB
```

---

## Resumen del capítulo

- Ubuntu 22.04 LTS (imagen oficial) es la opción recomendada para este libro.
- El proceso de grabación requiere verificar la integridad de la imagen y seleccionar el dispositivo correcto para no sobreescribir datos.
- El acceso SSH permite trabajar desde el PC de desarrollo sin necesidad de monitor ni teclado en la placa.
- Los 41 paquetes retenidos por `apt-mark hold` no deben modificarse: protegen los drivers de hardware propietarios.

## Ejercicios

1. Calcule el ancho de banda de escritura de la microSD comparando `dd if=/dev/zero of=test bs=4M count=256 oflag=direct` con los valores del benchmark de la tarjeta. ¿Coinciden?
2. Configure un hostname personalizado para la placa con `sudo hostnamectl set-hostname mi-orangepi` y verifique que el cambio persiste tras un reinicio.
3. Escriba un script Bash que muestre la temperatura máxima de todas las zonas térmicas cada 5 segundos, con una alerta si supera los 80°C.
