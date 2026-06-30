# Capítulo 10 — Programación a Bajo Nivel: Demonios y Señales

## Objetivo

Al finalizar este capítulo el lector escribirá programas en C para Linux embebido, diseñará e implementará demonios del sistema (servicios systemd) y manejará señales del kernel para crear procesos robustos.

---

## 10.1 C para Linux embebido

Python es ideal para prototipado y aplicaciones de alto nivel. C es necesario cuando:
- Se requiere latencia predecible (< 1 ms)
- Se interactúa directamente con llamadas del sistema sin overhead
- Se escribe código que se ejecutará en el espacio del kernel (capítulo 11)
- El rendimiento de la CPU es el cuello de botella

### Compilación cruzada de un programa C

```bash
# En el PC de desarrollo
cat > hola_rk3588.c << 'EOF'
#include <stdio.h>
#include <sys/utsname.h>

int main(void) {
    struct utsname info;
    uname(&info);
    printf("Sistema: %s %s (%s)\n", info.sysname, info.release, info.machine);
    return 0;
}
EOF

aarch64-linux-gnu-gcc -O2 -o hola_rk3588 hola_rk3588.c
file hola_rk3588
# hola_rk3588: ELF 64-bit LSB executable, ARM aarch64

# Copiar y ejecutar en la placa
scp hola_rk3588 orangepi@192.168.1.105:~/
ssh orangepi@192.168.1.105 ./hola_rk3588
```

---

## 10.2 Control de GPIO desde C con libgpiod

```c
// gpio_parpadeo.c
#include <gpiod.h>
#include <stdio.h>
#include <unistd.h>

#define CHIP  "/dev/gpiochip3"
#define LINEA  1   // GPIO3_A1, pin físico 12

int main(void) {
    struct gpiod_chip *chip;
    struct gpiod_line *linea;
    int ciclo = 0;

    chip = gpiod_chip_open(CHIP);
    if (!chip) {
        perror("gpiod_chip_open");
        return 1;
    }

    linea = gpiod_chip_get_line(chip, LINEA);
    if (!linea) {
        perror("gpiod_chip_get_line");
        gpiod_chip_close(chip);
        return 1;
    }

    if (gpiod_line_request_output(linea, "gpio-c", 0) < 0) {
        perror("gpiod_line_request_output");
        gpiod_chip_close(chip);
        return 1;
    }

    while (1) {
        printf("Ciclo %d: ALTO\n", ++ciclo);
        gpiod_line_set_value(linea, 1);
        sleep(1);

        printf("Ciclo %d: BAJO\n", ciclo);
        gpiod_line_set_value(linea, 0);
        sleep(1);
    }

    gpiod_line_release(linea);
    gpiod_chip_close(chip);
    return 0;
}
```

```bash
aarch64-linux-gnu-gcc -O2 -o gpio_parpadeo gpio_parpadeo.c -lgpiod
```

---

## 10.3 Llamadas del sistema para periféricos

Todos los periféricos de Linux son archivos. Las llamadas del sistema `open()`, `read()`, `write()`, `ioctl()` y `close()` son la interfaz universal:

```c
// Leer temperatura desde sysfs
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

float leer_temperatura(const char *ruta) {
    char buffer[16];
    int fd = open(ruta, O_RDONLY);
    if (fd < 0) return -1.0f;

    ssize_t n = read(fd, buffer, sizeof(buffer) - 1);
    close(fd);

    if (n <= 0) return -1.0f;
    buffer[n] = '\0';

    return atof(buffer) / 1000.0f;   // milicélsius → Celsius
}

int main(void) {
    float temp = leer_temperatura("/sys/class/thermal/thermal_zone0/temp");
    printf("Temperatura del SoC: %.1f°C\n", temp);
    return 0;
}
```

---

## 10.4 Señales del sistema operativo

Las señales son notificaciones asíncronas que el kernel envía a los procesos. Son fundamentales para crear demonios robustos.

**Señales más importantes:**

| Señal | Número | Uso típico |
|---|---|---|
| `SIGTERM` | 15 | Terminación ordenada (systemd stop) |
| `SIGKILL` | 9 | Terminación forzada (no interceptable) |
| `SIGINT` | 2 | Ctrl+C desde el terminal |
| `SIGHUP` | 1 | Recargar configuración sin reiniciar |
| `SIGUSR1` | 10 | Señal de usuario definible |
| `SIGCHLD` | 17 | Un proceso hijo terminó |

### Manejo de señales con sigaction

```c
#include <signal.h>
#include <stdio.h>
#include <unistd.h>
#include <stdatomic.h>

static atomic_int ejecutando = 1;   // atomic: seguro con señales

static void manejador_senal(int senal) {
    if (senal == SIGTERM || senal == SIGINT) {
        ejecutando = 0;
    }
}

int main(void) {
    struct sigaction accion = {
        .sa_handler = manejador_senal,
        .sa_flags   = SA_RESTART,   // reiniciar syscalls interrumpidas
    };
    sigemptyset(&accion.sa_mask);

    sigaction(SIGTERM, &accion, NULL);
    sigaction(SIGINT,  &accion, NULL);

    printf("Proceso iniciado (PID %d). Esperando SIGTERM o Ctrl+C...\n", getpid());

    while (ejecutando) {
        // Lógica principal del daemon
        sleep(1);
    }

    printf("Señal recibida. Liberando recursos y terminando.\n");
    return 0;
}
```

---

## 10.5 Diseño de un demonio (daemon)

Un demonio es un proceso que se ejecuta en segundo plano, sin terminal de control, como servicio del sistema. El proceso de daemonización clásico en Unix sigue estos pasos:

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <syslog.h>

void daemonizar(void) {
    pid_t pid = fork();       // 1. Crear proceso hijo
    if (pid < 0) exit(EXIT_FAILURE);
    if (pid > 0) exit(EXIT_SUCCESS);   // padre termina

    setsid();                 // 2. Crear nueva sesión (sin terminal)

    pid = fork();             // 3. Segundo fork (previene re-adquirir terminal)
    if (pid < 0) exit(EXIT_FAILURE);
    if (pid > 0) exit(EXIT_SUCCESS);

    umask(0);                 // 4. Resetear máscara de permisos
    chdir("/");               // 5. Cambiar a directorio raíz

    // 6. Cerrar stdin/stdout/stderr y redirigir a /dev/null
    close(STDIN_FILENO);
    close(STDOUT_FILENO);
    close(STDERR_FILENO);
    open("/dev/null", O_RDONLY);
    open("/dev/null", O_WRONLY);
    open("/dev/null", O_WRONLY);

    openlog("mi-daemon", LOG_PID, LOG_DAEMON);
    syslog(LOG_INFO, "Daemon iniciado");
}
```

---

## 10.6 Servicio systemd: la forma moderna

En sistemas con systemd (como Ubuntu 22.04), el proceso de daemonización manual es innecesario. systemd gestiona el ciclo de vida del proceso. El programa solo necesita manejar `SIGTERM` para una terminación ordenada.

```ini
# /etc/systemd/system/monitor-temperatura.service
[Unit]
Description=Monitor de temperatura Orange Pi 5 Plus
After=multi-user.target

[Service]
Type=simple
User=orangepi
ExecStart=/usr/local/bin/monitor_temperatura
Restart=on-failure
RestartSec=5s

# Limit de recursos
LimitCPU=30s
MemoryMax=32M

# Seguridad: aislamiento del proceso
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now monitor-temperatura
sudo systemctl status monitor-temperatura
journalctl -u monitor-temperatura -f
```

---

## 10.7 Comunicación entre procesos (IPC)

Los demonios frecuentemente necesitan comunicarse con otros procesos o con la interfaz de usuario.

### Pipes con nombre (FIFO)

```c
// Proceso escritor (daemon)
#include <fcntl.h>
#include <stdio.h>
#include <sys/stat.h>

#define FIFO_PATH "/tmp/temperatura.fifo"

int main(void) {
    mkfifo(FIFO_PATH, 0666);
    int fd = open(FIFO_PATH, O_WRONLY);

    char buffer[64];
    while (1) {
        snprintf(buffer, sizeof(buffer), "TEMP:65.2\n");
        write(fd, buffer, strlen(buffer));
        sleep(1);
    }
    return 0;
}
```

```bash
# Leer desde la FIFO (cualquier proceso)
cat /tmp/temperatura.fifo
```

---

## Resumen del capítulo

- C es el lenguaje de elección para aplicaciones de baja latencia, drivers del kernel y código con requisitos de rendimiento estrictos.
- Las señales (`SIGTERM`, `SIGINT`, `SIGHUP`) son el mecanismo estándar para comunicación entre el sistema y los procesos.
- El manejo correcto de señales con `sigaction` y variables atómicas es esencial para crear demonios robustos.
- systemd elimina la necesidad de la daemonización manual: el proceso solo necesita manejar `SIGTERM`.

## Ejercicios

1. Compile y ejecute `gpio_parpadeo.c` en la placa. Envíele la señal `SIGTERM` con `kill $(pgrep gpio_parpadeo)`. ¿Qué ocurre? ¿Por qué no termina de forma ordenada? Modifique el código para manejarlo correctamente.
2. Cree un servicio systemd que ejecute el monitor de temperatura del capítulo 7. Configure `Restart=always` y verifique que se reinicia automáticamente si se mata el proceso con `kill -9`.
3. Implemente un daemon que lea la temperatura del SoC cada segundo y la escriba en una FIFO `/tmp/temp.fifo`. Escriba un cliente en Python que lea de esa FIFO y muestre una alerta cuando la temperatura supere los 75°C.
