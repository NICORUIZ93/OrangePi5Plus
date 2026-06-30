# Capítulo 3 — Dominando Linux para la Orange Pi

## Objetivo

Al finalizar este capítulo el lector navegará con fluidez el sistema de archivos de Linux, gestionará procesos y servicios, y escribirá scripts Bash para automatizar tareas de monitoreo del sistema.

---

## 3.1 Filosofía Linux y su importancia en sistemas embebidos

Linux sigue la filosofía Unix: **un programa hace una cosa y la hace bien**. Los programas se comunican mediante tuberías de texto (`|`), y casi todo el estado del sistema es accesible a través del sistema de archivos.

Este principio es especialmente importante en sistemas embebidos: los periféricos del RK3588 (GPIO, PWM, LEDs, sensores térmicos) se controlan leyendo y escribiendo archivos en `/dev/` y `/sys/`. No se necesita una API especial: basta con `echo` y `cat`.

```bash
# Ejemplo: apagar el LED verde de la placa sin Python
echo "none"       | sudo tee /sys/class/leds/green_led/trigger
echo "0"          | sudo tee /sys/class/leds/green_led/brightness

# Leer la temperatura del CPU sin instalar nada
cat /sys/class/thermal/thermal_zone0/temp
```

---

## 3.2 Estructura del sistema de archivos

Linux organiza todos los archivos en un árbol jerárquico que parte de la raíz `/`. A diferencia de Windows, no existen letras de unidad: los discos, memorias USB y sistemas de archivos de red se montan en directorios dentro de este árbol.

```
/
├── bin/        → Ejecutables esenciales del sistema (ls, cp, bash…)
├── boot/       → Kernel, initramfs, u-boot, orangepiEnv.txt
├── dev/        → Archivos de dispositivo (tty, sda, gpiochip, i2c, spidev…)
├── etc/        → Archivos de configuración del sistema
├── home/       → Directorios personales de los usuarios
├── lib/        → Bibliotecas compartidas
├── proc/       → Sistema de archivos virtual: estado del kernel en tiempo real
├── sys/        → Sistema de archivos virtual: árbol de dispositivos del kernel
├── tmp/        → Archivos temporales (se borra al reiniciar)
├── usr/        → Programas y datos de usuario instalados
└── var/        → Datos variables: logs, bases de datos, colas de impresión
```

### /dev: archivos de dispositivo

Cada pieza de hardware del sistema aparece como un archivo en `/dev/`. Escribir o leer ese archivo equivale a comunicarse con el hardware:

```
/dev/
├── gpiochip0 … gpiochip5  → Bancos GPIO del RK3588
├── i2c-0 … i2c-9          → Buses I2C
├── spidev0.0, spidev0.1   → Bus SPI con dos chip-selects
├── ttyS0 … ttyS9          → Puertos serie UART
├── mmcblk0                → MicroSD
├── nvme0                  → Disco NVMe (si está conectado)
└── video0, video1         → Cámaras o decodificador de video
```

### /sys: árbol de dispositivos del kernel

`/sys` es un sistema de archivos virtual que expone la estructura interna del kernel. Cada archivo representa un atributo de un dispositivo o subsistema:

```
/sys/class/
├── leds/             → LEDs del sistema (green_led, blue_led)
├── pwm/              → Controladores PWM
├── thermal/          → Zonas térmicas y sensores de temperatura
├── gpio/             → Estado de líneas GPIO (legacy, prefer /dev/gpiochip)
└── net/              → Interfaces de red (eth0, wlan0)
```

### /proc: estado del kernel en tiempo real

```
/proc/
├── cpuinfo         → Información detallada de los núcleos CPU
├── meminfo         → Estado de la memoria RAM
├── modules         → Módulos del kernel cargados
├── interrupts      → Contador de interrupciones por dispositivo
├── net/dev         → Estadísticas de red
└── <PID>/          → Un directorio por cada proceso en ejecución
```

### /boot: archivos de arranque

```
/boot/
├── Image                    → Kernel Linux (imagen comprimida)
├── uInitrd                  → Disco RAM inicial (initramfs)
├── dtb/rockchip/            → Device Tree Blobs (descripción del hardware)
└── orangepiEnv.txt          → Configuración de overlays y parámetros del kernel
```

---

## 3.3 Comandos esenciales del terminal

### Navegación del sistema de archivos

```bash
pwd                 # Mostrar directorio actual (Print Working Directory)
ls -lah             # Listar archivos con detalles, incluyendo ocultos
ls -lah /dev/gpio*  # Listar archivos que coinciden con un patrón
cd /ruta/destino    # Cambiar de directorio
cd ~                # Ir al directorio personal
cd -                # Volver al directorio anterior
tree -L 2           # Árbol de directorios, máximo 2 niveles de profundidad
```

### Gestión de archivos y directorios

```bash
cp origen destino          # Copiar archivo
cp -r directorio destino   # Copiar directorio (recursivo)
mv origen destino          # Mover o renombrar
rm archivo                 # Eliminar archivo
rm -rf directorio          # Eliminar directorio y su contenido (¡usar con cuidado!)
mkdir -p ruta/sub/dir      # Crear directorio y subdirectorios si no existen
cat archivo.txt            # Mostrar contenido completo
less archivo.txt           # Ver archivo paginado (q para salir)
head -20 archivo.txt       # Primeras 20 líneas
tail -f /var/log/syslog    # Últimas líneas, actualizándose en tiempo real
```

### Búsqueda

```bash
find /sys -name "*pwm*"          # Buscar archivos por nombre
find /dev -type c                # Buscar character devices
grep -r "rknpu" /etc/            # Buscar texto en archivos
grep -n "error" log.txt          # Mostrar líneas con número de línea
which python3                    # Ruta de un ejecutable
```

### Gestión de procesos

```bash
ps aux                           # Lista de todos los procesos
ps aux | grep python3            # Filtrar por nombre
top                              # Monitor de procesos (q para salir)
htop                             # Monitor mejorado (requiere: sudo apt install htop)
kill PID                         # Enviar señal SIGTERM al proceso
kill -9 PID                      # Señal SIGKILL (forzar terminación)
pgrep python3                    # PIDs de procesos con ese nombre
```

### Gestión de servicios (systemd)

```bash
sudo systemctl status ssh           # Estado del servicio SSH
sudo systemctl start  servicio      # Iniciar
sudo systemctl stop   servicio      # Detener
sudo systemctl enable servicio      # Habilitar al arranque
sudo systemctl disable servicio     # Deshabilitar del arranque
sudo systemctl restart servicio     # Reiniciar
journalctl -u servicio -f           # Ver logs del servicio en tiempo real
journalctl -xe                      # Logs recientes con contexto de errores
```

### Permisos y usuarios

```bash
ls -l archivo                # Ver permisos (rwxrwxrwx = usuario/grupo/otros)
chmod 755 script.sh          # rwxr-xr-x: ejecutable por todos
chmod +x script.sh           # Agregar permiso de ejecución
chown usuario:grupo archivo  # Cambiar propietario
sudo comando                 # Ejecutar como root
su - usuario                 # Cambiar de usuario
groups                       # Grupos del usuario actual
sudo usermod -aG gpio orangepi  # Agregar usuario a un grupo
```

### Información del sistema

```bash
uname -a                     # Versión del kernel y arquitectura
lscpu                        # Detalles del procesador
free -h                      # Memoria RAM
df -h                        # Espacio en disco
lsblk                        # Dispositivos de almacenamiento
ip addr show                 # Interfaces de red y direcciones IP
lsusb                        # Dispositivos USB
lspci                        # Dispositivos PCIe
dmesg | tail -50             # Últimos mensajes del kernel
dmesg | grep rknpu           # Filtrar mensajes del driver NPU
```

---

## 3.4 Tuberías, redirección y filtros

La potencia de Linux proviene de combinar comandos sencillos con tuberías (`|`) y redirección:

```bash
# Tubería: la salida de un comando es la entrada del siguiente
dmesg | grep -i "error" | tail -20

# Redirección de salida: guardar en archivo
ls -la > lista_archivos.txt

# Redirección de entrada: leer de archivo
sort < lista_archivos.txt

# Redirección de salida de tee: escribir en archivo Y ver en pantalla
echo "pwm14-m0" | sudo tee /boot/orangepiEnv.txt

# Redirigir stderr a /dev/null (silenciar errores)
comando 2>/dev/null

# Combinar todo
cat /proc/cpuinfo | grep "CPU part" | sort | uniq -c
```

---

## 3.5 Scripting en Bash

Bash permite automatizar secuencias de comandos, crear herramientas de monitoreo y gestionar el sistema. Un script Bash es un archivo de texto ejecutable que el shell interpreta línea por línea.

### Estructura básica

```bash
#!/bin/bash
# La primera línea (shebang) indica qué intérprete usar

# Variables
PLACA="Orange Pi 5 Plus"
UMBRAL=80

# Imprimir con formato
echo "Monitoreando: $PLACA"
printf "Umbral de temperatura: %d°C\n" $UMBRAL
```

### Control de flujo

```bash
#!/bin/bash
# Condicional
temperatura=$(cat /sys/class/thermal/thermal_zone0/temp)
temp_c=$((temperatura / 1000))

if [ $temp_c -gt 80 ]; then
    echo "ALERTA: CPU a $temp_c°C"
elif [ $temp_c -gt 70 ]; then
    echo "Advertencia: CPU a $temp_c°C"
else
    echo "Temperatura normal: $temp_c°C"
fi

# Bucle while
contador=0
while [ $contador -lt 5 ]; do
    echo "Iteración $contador"
    contador=$((contador + 1))
    sleep 1
done

# Bucle for sobre archivos
for zona in /sys/class/thermal/thermal_zone*/; do
    tipo=$(cat "$zona/type")
    temp=$(( $(cat "$zona/temp") / 1000 ))
    echo "$tipo: $temp°C"
done
```

### Script práctico: monitor de temperatura

Guardar como `monitor_temp.sh`:

```bash
#!/bin/bash
# Monitor de temperatura para Orange Pi 5 Plus
# Uso: ./monitor_temp.sh [umbral_celsius]

UMBRAL=${1:-80}   # Parámetro con valor por defecto

echo "Monitor de temperatura (umbral: ${UMBRAL}°C) — Ctrl+C para salir"
echo "-------------------------------------------------------------------"

while true; do
    timestamp=$(date "+%H:%M:%S")
    printf "[%s] " "$timestamp"

    max_temp=0
    for zona in /sys/class/thermal/thermal_zone*/; do
        tipo=$(cat "$zona/type" 2>/dev/null)
        raw=$(cat "$zona/temp" 2>/dev/null)
        temp=$((raw / 1000))

        printf "%s:%d°C  " "$tipo" "$temp"

        if [ $temp -gt $max_temp ]; then
            max_temp=$temp
        fi
    done

    if [ $max_temp -gt $UMBRAL ]; then
        printf " ⚠ ALERTA\n"
    else
        printf "\n"
    fi

    sleep 3
done
```

```bash
chmod +x monitor_temp.sh
./monitor_temp.sh 75     # Alerta si supera 75°C
```

---

## 3.6 Gestión de paquetes con APT

```bash
sudo apt update                     # Actualizar lista de paquetes
sudo apt upgrade                    # Instalar actualizaciones disponibles
sudo apt install paquete            # Instalar un paquete
sudo apt remove paquete             # Desinstalar (conserva configuración)
sudo apt purge paquete              # Desinstalar (elimina configuración)
sudo apt autoremove                 # Eliminar dependencias huérfanas
apt search término                  # Buscar paquetes por nombre/descripción
apt show paquete                    # Información detallada de un paquete
dpkg -l | grep nombre               # Verificar si un paquete está instalado
```

---

## 3.7 Crontab: tareas programadas

```bash
crontab -e       # Editar tabla de tareas del usuario actual
crontab -l       # Listar tareas programadas
```

Formato de una entrada de crontab:

```
# m  h  dom  mon  dow   comando
# ┬  ┬   ┬    ┬    ┬
# │  │   │    │    └── Día de la semana (0-7, 0=domingo)
# │  │   │    └─────── Mes (1-12)
# │  │   └──────────── Día del mes (1-31)
# │  └──────────────── Hora (0-23)
# └─────────────────── Minuto (0-59)

# Ejecutar monitor_temp.sh cada 5 minutos, guardar log
*/5 * * * * /home/orangepi/monitor_temp.sh >> /var/log/temperatura.log 2>&1

# Ejecutar un script al arranque del sistema
@reboot /home/orangepi/inicio.sh
```

---

## Resumen del capítulo

- En Linux, casi todo el hardware es accesible como archivos en `/dev/` y `/sys/`. Esta propiedad es la base de todos los capítulos de hardware del libro.
- Los comandos esenciales (`ls`, `cat`, `grep`, `find`, `ps`, `systemctl`) son suficientes para gestionar la mayoría de las tareas cotidianas.
- Las tuberías (`|`) permiten combinar comandos sencillos para realizar tareas complejas.
- Los scripts Bash automatizan secuencias repetitivas y son la herramienta más directa para gestionar el sistema.

## Ejercicios

1. Escriba un script Bash que muestre, cada 10 segundos, la frecuencia actual de cada núcleo CPU (`/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq`) junto con su temperatura.
2. Use `find` para localizar todos los archivos de configuración en `/etc/` modificados en los últimos 7 días.
3. Cree un servicio systemd que ejecute el script de monitoreo de temperatura al arrancar la placa y que reinicie automáticamente si termina inesperadamente. Consulte la documentación de `systemd.service` para las directivas `Restart=` y `RestartSec=`.
