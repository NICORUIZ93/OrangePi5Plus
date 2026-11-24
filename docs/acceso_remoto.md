# Acceso remoto headless a la Orange Pi 5 Plus

Esta guía documenta cómo entrar a la placa **sin monitor**, tanto por SSH como
por consola serial. **No incluye contraseñas**: guárdalas en tu gestor de
contraseñas o en un archivo local ignorado por Git (ver `.gitignore`).

## Datos de la placa

| Campo | Valor |
|---|---|
| Modelo | Orange Pi 5 Plus (Rockchip RK3588) |
| Hostname | `orangepi5plus` |
| Usuario por defecto | `orangepi` |
| Contraseña por defecto de la imagen | `orangepi` (cámbiala en el primer arranque) |
| Interfaces Ethernet | `enP4p65s0`, `enP3p49s0` (ambas en DHCP) |
| WiFi | `wlx90916440b20e` (perfiles guardados, ver `nmcli con show`) |
| SSH | Habilitado por defecto en la imagen oficial |

## Situación que motivó esta guía

Tras cambiar de router, la placa quedó sin IP: el enlace directo Mac↔Pi no
tiene servidor DHCP, por lo que la Pi no obtiene dirección y no responde ni por
IPv6 link-local ni por mDNS.

## Método 1: DHCP temporal desde el Mac (funcionó)

1. Conectar cable RJ45 directo Mac ↔ Orange Pi.
2. Identificar el puerto Ethernet del Mac (`en8` en el equipo de prueba):
   ```sh
   networksetup -listallhardwareports | grep -A1 "Ethernet Adapter"
   ifconfig en8
   ```
3. Asignar IP fija al Mac y levantar un DHCP mínimo con `dnsmasq`:
   ```sh
   sudo ifconfig en8 inet 192.168.1.10 netmask 255.255.255.0
   brew install dnsmasq
   ```
   Configuración (`/usr/local/etc/dnsmasq.conf` o un archivo propio):
   ```ini
   interface=en8
   bind-interfaces
   listen-address=192.168.1.10
   dhcp-range=192.168.1.100,192.168.1.200,12h
   dhcp-option=3,192.168.1.10
   dhcp-option=6,8.8.8.8
   log-facility=/path/a/dnsmasq.log
   ```
   ```sh
   sudo dnsmasq -C /path/a/dnsmasq.conf
   ```
4. Desconectar y reconectar el cable en la Pi (o reiniciarla) para forzar un
   `DHCPDISCOVER`. En el log debe aparecer `DHCPACK ... orangepi5plus`.
5. Buscar la IP asignada y entrar:
   ```sh
   fping -g -r 0 -t 100 192.168.1.100 192.168.1.200 | grep alive
   ssh orangepi@192.168.1.114
   ```
   Con `sshpass` (instalado con Homebrew):
   ```sh
   sshpass -p '<PASSWORD>' ssh orangepi@<IP_DE_LA_PI>
   ```

## Método 2: cable directo a IP fija conocida

Si la Pi conserva una IP fija de la red anterior:

```sh
sudo ifconfig en8 inet <RED_VIEJA>.10 netmask 255.255.255.0
seq 1 254 | xargs -P 20 -I{} sh -c \
  'nc -z -G 1 <RED_VIEJA>.{} 22 2>/dev/null && echo "<RED_VIEJA>.{} SSH"'
ssh orangepi@<IP>
```

## Método 3: consola serial (sin red)

En Orange Pi 5 Plus el debug UART es un **header de 3 pines separado** (no los
pines 6/8/10 del expansion header, que aplica a 5 Max / 5 Pro).

| Parámetro | Valor |
|---|---|
| Velocidad | **1.500.000 baud** (`ttyS2`) |
| Niveles | 3.3 V |
| Conexión | GND, TX→RX, RX→TX (no conectar VCC) |

```sh
screen /dev/cu.usbserial-* 1500000
```

El parámetro `console=` se define en `/boot/orangepiEnv.txt` (`display`,
`serial` o `both`; por defecto `both`).

## Dejar la placa en la red nueva

Dentro de la Pi, con NetworkManager:

```sh
nmcli con show
nmcli con mod "Wired connection 2" ipv4.method auto
nmcli con up "Wired connection 2"
ip -4 addr show enP4p65s0
```

Para WiFi:

```sh
nmcli dev wifi connect "<SSID>" password "<PASSWORD>"
```

Luego reconectar el cable al router y volver a escanear la subred desde el Mac.

## Seguridad

- No versionar contraseñas. Usar `.env` (ignorado por Git) o el llavero del
  sistema.
- Cambiar la contraseña por defecto `orangepi` después del primer acceso:
  ```sh
  passwd orangepi
  ```
- Preferir claves SSH:
  ```sh
  ssh-keygen -t ed25519 -C "orangepi5plus"
  ssh-copy-id orangepi@<IP>
  ```
