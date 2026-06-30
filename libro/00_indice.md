# De Cero a Experto con Orange Pi 5 Plus
## Índice general

**Plataforma:** Orange Pi 5 Plus (RK3588)  
**Sistema operativo de referencia:** Ubuntu 22.04.5 LTS  
**Lenguaje principal:** Python 3.10 · C (capítulos avanzados)

---

## PARTE 1 — Los Cimientos del Poder
*Nivel: Principiante. Sin conocimientos previos de Linux ni electrónica.*

| Capítulo | Título | Archivo | Tiempo est. |
|---|---|---|---|
| 1 | Presentando la Orange Pi 5 Plus | [cap01_presentacion.md](cap01_presentacion.md) | 1 h |
| 2 | Puesta en marcha y primer contacto | [cap02_puesta_en_marcha.md](cap02_puesta_en_marcha.md) | 2 h |
| 3 | Dominando Linux para la Orange Pi | [cap03_linux.md](cap03_linux.md) | 3 h |
| 4 | El entorno de desarrollo en Python | [cap04_python.md](cap04_python.md) | 2 h |

**Subtotal Parte 1: ~8 horas**

## PARTE 2 — Conquistando el Hardware
*Nivel: Intermedio. Requiere haber completado la Parte 1.*

| Capítulo | Título | Archivo | Código | Tiempo est. |
|---|---|---|---|---|
| 5 | El corazón de la electrónica: GPIO | [cap05_gpio.md](cap05_gpio.md) | `01_gpio_salida.py` · `02_gpio_entrada.py` | 3 h |
| 6 | Comunicación con el mundo: I2C, SPI y PWM | [cap06_comunicacion.md](cap06_comunicacion.md) | `03_pwm_servo.py` · `04_i2c_escaneo.py` · `05_i2c_oled.py` · `06_spi_loopback.py` | 4 h |
| 7 | Los componentes integrados de la placa | [cap07_integrados.md](cap07_integrados.md) | `07_leds_integrados.py` | 2 h |

**Subtotal Parte 2: ~9 horas** (requiere LED, resistencia 330Ω, pulsador, servo SG90, módulo OLED SSD1306 — costo aproximado de componentes: 15–20 USD)

## PARTE 3 — El Arte de la Ingeniería de Sistemas
*Nivel: Avanzado. Requiere conocimientos de C y familiaridad con el kernel Linux.*

| Capítulo | Título | Archivo | Tiempo est. |
|---|---|---|---|
| 8 | Compilación cruzada y el bootloader | [cap08_compilacion.md](cap08_compilacion.md) | 4 h* |
| 9 | Creando tu propio sistema con Buildroot | [cap09_buildroot.md](cap09_buildroot.md) | 5 h* |
| 10 | Programación a bajo nivel: demonios y señales | [cap10_bajo_nivel.md](cap10_bajo_nivel.md) | 3 h |
| 11 | El mundo de los drivers de dispositivo | [cap11_drivers.md](cap11_drivers.md) | 3 h |

**Subtotal Parte 3: ~15 horas** (*incluye tiempo de compilación en background, no solo lectura/escritura activa)

## PARTE 4 — Inteligencia Artificial y Proyectos Finales
*Nivel: Experto. Integra todos los conocimientos anteriores.*

| Capítulo | Título | Archivo | Código | Tiempo est. |
|---|---|---|---|---|
| 12 | Inteligencia artificial en el edge con la NPU | [cap12_npu.md](cap12_npu.md) | `08_npu_inferencia.py` | 3 h |
| 13 | Proyectos finales integradores | [cap13_proyectos.md](cap13_proyectos.md) | — | 6 h+ |

**Subtotal Parte 4: ~9 horas** (los tres proyectos del capítulo 13 pueden trabajarse en paralelo o por separado)

---

**Tiempo total estimado: ~41 horas** de trabajo activo, equivalente a un curso universitario de un semestre con dedicación de 3 horas semanales.

---

## Mapa de dependencias entre capítulos

```
Cap 1 → Cap 2 → Cap 3 → Cap 4
                          ↓
              Cap 5 → Cap 6 → Cap 7
                                ↓
              Cap 8 → Cap 9 → Cap 10 → Cap 11
                                          ↓
                                       Cap 12 → Cap 13
```

## Cómo usar este libro

Cada capítulo sigue la misma estructura pedagógica:

1. **Objetivo** — qué aprenderá el lector al terminar el capítulo
2. **Fundamentos** — teoría necesaria para entender el práctico
3. **Implementación** — código paso a paso con explicaciones
4. **Verificación** — cómo confirmar que funciona correctamente
5. **Ejercicios** — retos para consolidar el aprendizaje

Los archivos Python del repositorio (`01_gpio_salida.py` … `08_npu_inferencia.py`) son el **complemento práctico** de este libro. Cada capítulo los referencia y los explica en detalle.

## Configuración inicial del sistema

Antes de comenzar la Parte 2, ejecutar una vez:

```bash
./setup_gpio_permissions.sh && sudo reboot   # Capítulos 5, 6, 7
./setup_npu.sh                               # Capítulo 12
```
