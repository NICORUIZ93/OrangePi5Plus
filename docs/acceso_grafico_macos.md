# Acceso gráfico desde macOS

Esta guía deja la Orange Pi 5 Plus accesible desde un MacBook mediante RDP
usando Microsoft Remote Desktop / Windows App.

## Estado validado

Configuración probada en esta placa:

| Componente | Estado |
|---|---|
| Sistema | Ubuntu 22.04.5 LTS |
| Escritorio local | GNOME con LightDM |
| Protocolo remoto | RDP |
| Servicio | `xrdp` |
| Backend gráfico | `Xvnc` con TigerVNC |
| Sesión remota | XFCE |
| Puerto | `3389/tcp` |

Se usa `Xvnc` como backend de XRDP porque el backend `Xorg` intenta abrir una
consola virtual y en esta imagen RK3588 falla con permisos de consola. `Xvnc`
evita ese problema y funciona de forma estable para sesiones remotas.

## Instalación en la Orange Pi

```bash
sudo apt update
sudo apt install -y \
    xrdp \
    xorgxrdp \
    xfce4 \
    xfce4-goodies \
    dbus-x11 \
    tigervnc-standalone-server \
    tigervnc-common
```

Configurar XFCE como sesión del usuario:

```bash
echo startxfce4 > ~/.xsession
chmod 644 ~/.xsession
```

Permitir a XRDP leer su certificado y reiniciar servicios:

```bash
sudo adduser xrdp ssl-cert
sudo systemctl enable --now xrdp xrdp-sesman
sudo systemctl restart xrdp xrdp-sesman
```

## Usar Xvnc como sesión predeterminada

En `/etc/xrdp/xrdp.ini`, dejar la sección `[Xvnc]` antes de `[Xorg]`.
La sección debe verse así:

```ini
[Xvnc]
name=Xvnc
lib=libvnc.so
username=ask
password=ask
ip=127.0.0.1
port=-1
```

`[Xorg]` puede permanecer en el archivo como alternativa, pero no debe ser la
primera opción para esta placa.

## Conexión desde macOS

1. Instalar **Windows App** o **Microsoft Remote Desktop** desde la App Store.
2. Crear una conexión nueva.
3. Usar la IP de la Orange Pi.

Para consultar la IP en la placa:

```bash
hostname -I
```

Ejemplo:

```text
PC name: 172.20.10.2
User account: orangepi
Password: contraseña del usuario orangepi
```

Si aparece selector de sesión en la pantalla de XRDP, elegir `Xvnc`.

## Verificación

En la placa:

```bash
systemctl is-active xrdp xrdp-sesman
systemctl is-enabled xrdp xrdp-sesman
ss -ltnp | grep ':3389'
```

Resultado esperado:

```text
active
active
enabled
enabled
LISTEN ... *:3389 ...
```

Desde otra máquina en la misma red:

```bash
nc -zv <IP_DE_LA_PLACA> 3389
```

Durante una sesión remota activa deben aparecer procesos como:

```bash
pgrep -a Xvnc
pgrep -a xfce4-session
pgrep -a xfwm4
pgrep -a xfdesktop
```

## Diagnóstico

Ver logs de XRDP:

```bash
sudo tail -n 120 /var/log/xrdp.log /var/log/xrdp-sesman.log
```

Una sesión correcta muestra líneas como:

```text
login successful for display 10
loaded module 'libvnc.so'
VNC connection complete, connected ok
Session started successfully for user orangepi on display 10
```

Si el log muestra:

```text
xf86OpenConsole: Cannot open virtual console 2 (Permission denied)
```

entonces se está usando el backend `Xorg`. Cambiar a `Xvnc` como opción
predeterminada en `/etc/xrdp/xrdp.ini`.
