# Capítulo 11 — El Mundo de los Drivers de Dispositivo

## Objetivo

Al finalizar este capítulo el lector comprenderá la arquitectura del espacio de kernel en Linux, escribirá un módulo "Hola, Mundo" para el kernel, y desarrollará un driver básico de character device que exponga un periférico a través de `/dev/`.

---

## 11.1 Espacio de kernel vs. espacio de usuario

Linux divide el sistema en dos dominios de ejecución con diferentes niveles de privilegio:

```
┌─────────────────────────────────────────────────────────┐
│                  ESPACIO DE USUARIO                     │
│                                                         │
│   Aplicaciones Python, C, servicios, shells             │
│   Acceso a hardware: solo a través de /dev/ y /sys/     │
│   Un fallo solo afecta al proceso actual                │
│                                                         │
│           syscall: read(), write(), ioctl()             │
├─────────────────────────────────────────────────────────┤
│                  ESPACIO DE KERNEL                      │
│                                                         │
│   Drivers de dispositivo, subsistemas del kernel        │
│   Acceso directo a hardware, interrupciones, DMA        │
│   Un fallo provoca kernel panic (todo el sistema cae)   │
│                                                         │
│   Módulos: rknpu, i2c-rk3x, pwm-rockchip, gpiod…       │
└─────────────────────────────────────────────────────────┘
```

Un **módulo del kernel** (`.ko`) es código que se ejecuta en espacio de kernel. Se puede cargar y descargar en tiempo de ejecución sin reiniciar el sistema.

---

## 11.2 Módulo "Hola, Mundo"

El módulo más simple demuestra la estructura fundamental de un driver de Linux.

```c
// hola_kernel.c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Estudiante");
MODULE_DESCRIPTION("Módulo de ejemplo para Orange Pi 5 Plus");
MODULE_VERSION("1.0");

static int __init hola_init(void) {
    // printk escribe en el ring buffer del kernel (visible con dmesg)
    // KERN_INFO es el nivel de prioridad del mensaje
    printk(KERN_INFO "hola_kernel: módulo cargado en el RK3588\n");
    return 0;   // 0 = éxito; negativo = error (el módulo no se carga)
}

static void __exit hola_exit(void) {
    printk(KERN_INFO "hola_kernel: módulo descargado\n");
}

// Registrar las funciones de inicio y fin
module_init(hola_init);
module_exit(hola_exit);
```

### Makefile para módulos del kernel

```makefile
# Makefile
obj-m := hola_kernel.o

# KERNELDIR debe apuntar al árbol de fuentes del kernel instalado
KERNELDIR ?= /lib/modules/$(shell uname -r)/build
PWD       := $(shell pwd)

all:
	$(MAKE) -C $(KERNELDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KERNELDIR) M=$(PWD) clean
```

### Compilar y probar en la placa

```bash
# En la placa (necesita los headers del kernel)
sudo apt install linux-headers-$(uname -r)

make

# Cargar el módulo
sudo insmod hola_kernel.ko

# Ver el mensaje en el ring buffer del kernel
dmesg | tail -5
# [ 1234.567] hola_kernel: módulo cargado en el RK3588

# Verificar que está cargado
lsmod | grep hola_kernel

# Descargar el módulo
sudo rmmod hola_kernel

dmesg | tail -2
# [ 1289.123] hola_kernel: módulo descargado
```

---

## 11.3 Parámetros del módulo

Los módulos pueden recibir parámetros en el momento de carga:

```c
#include <linux/moduleparam.h>

static int intervalo_ms = 1000;
module_param(intervalo_ms, int, S_IRUGO);
MODULE_PARM_DESC(intervalo_ms, "Intervalo en milisegundos (defecto: 1000)");

static int __init mi_init(void) {
    printk(KERN_INFO "Intervalo configurado: %d ms\n", intervalo_ms);
    return 0;
}
```

```bash
# Cargar con parámetro
sudo insmod mi_modulo.ko intervalo_ms=500

# Ver parámetros de un módulo cargado
cat /sys/module/mi_modulo/parameters/intervalo_ms
```

---

## 11.4 Driver de character device

Un character device es la abstracción del kernel para dispositivos que transfieren datos byte a byte (puertos serie, GPIO, sensores personalizados). Se expone como un archivo en `/dev/`.

```c
// driver_ejemplo.c
#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/uaccess.h>

MODULE_LICENSE("GPL");
#define DEVICE_NAME "mi_sensor"
#define CLASS_NAME  "sensores"

static dev_t   numero_device;
static struct cdev     mi_cdev;
static struct class   *mi_clase;
static struct device  *mi_device;

// Operación read: enviar datos al espacio de usuario
static ssize_t mi_read(struct file *f, char __user *buf,
                        size_t len, loff_t *offset) {
    char mensaje[] = "42.5\n";   // valor de sensor simulado
    size_t n = min(len, sizeof(mensaje) - 1);

    if (copy_to_user(buf, mensaje, n))
        return -EFAULT;

    return n;
}

// Tabla de operaciones del driver
static const struct file_operations mis_ops = {
    .owner = THIS_MODULE,
    .read  = mi_read,
};

static int __init driver_init(void) {
    // 1. Asignar número de device dinámicamente
    alloc_chrdev_region(&numero_device, 0, 1, DEVICE_NAME);

    // 2. Inicializar y registrar el character device
    cdev_init(&mi_cdev, &mis_ops);
    cdev_add(&mi_cdev, numero_device, 1);

    // 3. Crear la clase y el archivo /dev/mi_sensor automáticamente
    mi_clase  = class_create(THIS_MODULE, CLASS_NAME);
    mi_device = device_create(mi_clase, NULL, numero_device,
                               NULL, DEVICE_NAME);

    printk(KERN_INFO "%s: /dev/%s creado\n", DEVICE_NAME, DEVICE_NAME);
    return 0;
}

static void __exit driver_exit(void) {
    device_destroy(mi_clase, numero_device);
    class_unregister(mi_clase);
    class_destroy(mi_clase);
    cdev_del(&mi_cdev);
    unregister_chrdev_region(numero_device, 1);
    printk(KERN_INFO "%s: driver eliminado\n", DEVICE_NAME);
}

module_init(driver_init);
module_exit(driver_exit);
```

### Probar el driver desde espacio de usuario

```bash
# Compilar y cargar
make
sudo insmod driver_ejemplo.ko

# Verificar que el device apareció
ls -la /dev/mi_sensor

# Leer desde el driver (igual que cualquier archivo)
cat /dev/mi_sensor
# 42.5

# Con Python
python3 -c "print(open('/dev/mi_sensor').read())"
```

---

## 11.5 Drivers en el árbol del kernel: Device Tree binding

Para que un driver cargue automáticamente al arrancar (sin `insmod`), debe estar vinculado al Device Tree. El driver declara qué dispositivos maneja con una tabla `of_match_table`:

```c
#include <linux/of.h>
#include <linux/platform_device.h>

// Tabla de compatibilidad: coincide con la propiedad "compatible" del DT
static const struct of_device_id mi_sensor_ids[] = {
    { .compatible = "empresa,mi-sensor-v1" },
    { }   // centinela: fin de la tabla
};
MODULE_DEVICE_TABLE(of, mi_sensor_ids);

static struct platform_driver mi_driver = {
    .driver = {
        .name          = "mi-sensor",
        .of_match_table = mi_sensor_ids,
    },
    .probe  = mi_sensor_probe,   // llamado cuando se encuentra el hardware
    .remove = mi_sensor_remove,  // llamado al descargar
};

module_platform_driver(mi_driver);
```

Y en el Device Tree:

```dts
&i2c2 {
    mi-sensor@4A {
        compatible = "empresa,mi-sensor-v1";
        reg = <0x4A>;
    };
};
```

---

## Resumen del capítulo

- Los módulos del kernel se ejecutan en espacio de kernel con acceso directo al hardware. Un error puede causar kernel panic.
- La estructura básica es `module_init()` / `module_exit()` + funciones de operaciones del archivo.
- Los character devices exponen el hardware como archivos en `/dev/`, accesibles con `open()`, `read()`, `write()` desde cualquier lenguaje.
- El Device Tree binding permite al kernel cargar drivers automáticamente basándose en la descripción del hardware.

## Ejercicios

1. Compile y cargue el módulo `hola_kernel.ko` en la placa. Modifíquelo para que imprima el timestamp del kernel (`ktime_get()`) en cada carga y descarga.
2. Amplíe el driver de character device para implementar `write()`: que el usuario pueda escribir un número (1 o 0) en `/dev/mi_sensor` y que el driver lo imprima en el log del kernel.
3. Investigue el comando `strace cat /dev/mi_sensor`. ¿Qué llamadas al sistema usa `cat` para leer de un character device? ¿Coinciden con las funciones de la `file_operations` implementada?
