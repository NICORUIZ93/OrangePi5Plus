"""
Módulo 8 — Inferencia de redes neuronales en el NPU RK3588
===========================================================
Nivel: introductorio → avanzado  |  Sin conocimientos previos requeridos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ¿QUÉ ES EL NPU Y POR QUÉ IMPORTA?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Una red neuronal convolucional (CNN) como ResNet-18 realiza millones
de multiplicaciones y sumas por cada imagen que procesa. Una CPU de
propósito general puede hacer eso, pero desperdicia energía en
instrucciones de control, predicción de ramas y caché que las redes
neuronales no necesitan.

Un NPU (Neural Processing Unit) es un procesador especializado que
ejecuta SOLO multiplicaciones-acumulaciones (MACs) en paralelo masivo,
sin el overhead de una CPU. El RK3588 incluye una NPU de 6 TOPS:

    CPU (Cortex-A76, NEON):  ~4 GOPS  →  ~450 ms por imagen
    NPU (RK3588, INT8):      6 TOPS   →  ~5 ms por imagen
    Diferencia:              90× más rápido, con menos energía

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HOJA DE RUTA DE APRENDIZAJE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PASO 0  Verificar que el driver del NPU está cargado
  PASO 1  Descargar modelo y imagen de prueba
  PASO 2  Cargar el modelo .rknn en memoria
  PASO 3  Inicializar el driver del NPU
  PASO 4  Preprocesar la imagen → tensor de entrada
  PASO 5  Ejecutar inferencia y medir tiempo
  PASO 6  Interpretar el vector de salida (Top-5)

  [AVANZADO]  Aplicar softmax para obtener probabilidades reales
  [AVANZADO]  Medir rendimiento sostenido con N iteraciones
  [AVANZADO]  Comparar con inferencia en CPU

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PILA DE SOFTWARE (de alto a bajo nivel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Este script  (Python)
      ↓  llama a
  rknn-toolkit-lite2  →  RKNNLite  (biblioteca Python/C)
      ↓  llama a
  librknnrt.so  (runtime C de Rockchip)
      ↓  llama a
  driver rknpu  (módulo del kernel Linux)
      ↓  accede al
  NPU hardware  (3 núcleos × 2 TOPS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRERREQUISITOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Haber ejecutado: ./setup_npu.sh
  2. pip3 install opencv-python numpy

USO
  python3 08_npu_inferencia.py
"""

import os
import sys
import time
import urllib.request

# Silencia los mensajes I/W de librknnrt.so (nivel INFO y WARNING de la C lib).
# Debe establecerse ANTES de importar rknnlite para que la biblioteca los lea
# al inicializarse. Valores: 0=ninguno, 1=error, 2=warning, 3=info (defecto).
os.environ.setdefault("RKNN_LOG_LEVEL", "0")

import cv2
import numpy as np
from rknnlite.api import RKNNLite

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────

# URL base donde Rockchip publica los ejemplos oficiales de rknn-toolkit-lite2
REPO_BASE = (
    "https://raw.githubusercontent.com/airockchip/"
    "rknn-toolkit2/master/rknn-toolkit-lite2/examples/resnet18"
)

# Modelo ResNet-18 compilado para RK3588 con cuantización INT8.
# El archivo .rknn es un binario propio de Rockchip; no es el modelo original
# de PyTorch. Contiene los pesos cuantizados y el grafo de computación
# optimizado para el layout de memoria de la NPU del RK3588.
ARCHIVO_MODELO = "resnet18_for_rk3588.rknn"

# Imagen de prueba: un transbordador espacial, clase 812 en ImageNet.
# ImageNet es un conjunto de datos de 1.2 millones de imágenes en 1000 clases,
# usado como benchmark estándar de clasificación de imágenes.
ARCHIVO_IMAGEN = "space_shuttle_224.jpg"

# Cuántas predicciones mostrar (Top-K). Con K=5 se muestra el Top-5,
# métrica estándar en clasificación de ImageNet.
TOP_K = 5

# Diccionario parcial de etiquetas ImageNet (índice → nombre legible).
# El conjunto completo tiene 1000 clases; aquí solo las más conocidas.
ETIQUETAS = {
    0:   "tench (pez)",          1:   "goldfish (pez dorado)",
    207: "golden retriever",      208: "Labrador retriever",
    281: "tabby cat",             285: "Egyptian cat",
    386: "African elephant",      387: "Indian elephant",
    404: "airliner",              417: "balloon",
    508: "computer keyboard",     530: "digital watch",
    665: "missile",               670: "motor scooter",
    751: "racket",                762: "remote control",
    805: "soccer ball",           812: "space shuttle",
    850: "teddy bear",            895: "warplane",
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def descargar_si_falta(nombre_archivo: str, url: str) -> None:
    """
    Descarga un archivo solo si no existe localmente.
    Si la descarga falla a mitad, elimina el archivo parcial para que el
    próximo intento no encuentre un archivo corrupto.
    """
    if os.path.exists(nombre_archivo):
        return

    print(f"  ↓ Descargando {nombre_archivo} ...")
    try:
        urllib.request.urlretrieve(url, nombre_archivo)
    except Exception as error:
        if os.path.exists(nombre_archivo):
            os.remove(nombre_archivo)   # eliminar descarga parcial
        raise RuntimeError(
            f"No se pudo descargar {nombre_archivo}.\n"
            f"  URL: {url}\n"
            f"  Error: {error}"
        ) from error

    tamano_mb = os.path.getsize(nombre_archivo) / 1e6
    print(f"  ✓ {nombre_archivo} descargado ({tamano_mb:.1f} MB)")


def aplicar_softmax(vector: np.ndarray) -> np.ndarray:
    """
    Convierte puntajes crudos (logits) en probabilidades que suman 1.

    ¿Por qué softmax?
    -----------------
    La capa de salida de ResNet-18 produce un vector de 1000 valores
    llamados logits. Un logit es una medida relativa de "cuánto se parece
    esta imagen a esa clase". Los logits no son probabilidades: pueden ser
    negativos o muy grandes.

    Softmax transforma los logits en una distribución de probabilidad:
        P(clase_i) = exp(logit_i) / suma(exp(logit_j) para todo j)

    Resultado: cada valor queda en [0, 1] y todos suman exactamente 1.
    La clase con mayor logit sigue siendo la de mayor probabilidad.
    """
    e = np.exp(vector - np.max(vector))   # restar el máximo: estabilidad numérica
    return e / e.sum()


def nombre_clase(indice: int) -> str:
    """Retorna el nombre legible de una clase ImageNet, o el índice si no está en el dict."""
    return ETIQUETAS.get(indice, f"clase_{indice}")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 0 — VERIFICAR QUE EL DRIVER DEL NPU ESTÁ ACTIVO
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 65)
print("  Módulo 8: Inferencia en el NPU RK3588")
print("=" * 65)
print()

print("PASO 0 — Verificando dependencias del entorno...")

# En el BSP del RK3588 (kernel 5.10, driver rknpu 0.8.x), el driver no
# expone un character device en /dev/ verificable desde espacio de usuario.
# La disponibilidad real del hardware se confirma en PASO 3 cuando
# init_runtime() intenta abrir el driver. Si falla, el mensaje de error
# en PASO 3 indicará exactamente qué falta.
#
# Aquí solo verificamos las dependencias Python que deben estar presentes
# antes de intentar cualquier operación.

dependencias = {
    "numpy":      np,
    "cv2":        cv2,
    "rknnlite":   RKNNLite,
}

todas_ok = True
for nombre, modulo in dependencias.items():
    print(f"  ✓ {nombre} disponible")

# Verificar que librknnrt.so está accesible (lo usa rknnlite internamente)
import ctypes.util
lib = ctypes.util.find_library("rknnrt")
if lib:
    print(f"  ✓ librknnrt.so encontrada ({lib})")
else:
    print("  ⚠ librknnrt.so no encontrada en el path de librerías del sistema.")
    print("    Si PASO 3 falla, ejecute ./setup_npu.sh para instalarla.")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1 — DESCARGAR MODELO E IMAGEN DE PRUEBA
# ─────────────────────────────────────────────────────────────────────────────
print()
print("PASO 1 — Verificando archivos de recursos...")

# En la primera ejecución se descargan automáticamente (~12 MB en total).
# En ejecuciones posteriores, los archivos ya existen y se omite la descarga.
descargar_si_falta(ARCHIVO_MODELO, f"{REPO_BASE}/{ARCHIVO_MODELO}")
descargar_si_falta(ARCHIVO_IMAGEN, f"{REPO_BASE}/{ARCHIVO_IMAGEN}")

if os.path.exists(ARCHIVO_MODELO):
    print(f"  ✓ Modelo  : {ARCHIVO_MODELO}  ({os.path.getsize(ARCHIVO_MODELO) / 1e6:.1f} MB)")
if os.path.exists(ARCHIVO_IMAGEN):
    print(f"  ✓ Imagen  : {ARCHIVO_IMAGEN}  ({os.path.getsize(ARCHIVO_IMAGEN) / 1e3:.0f} KB)")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2 — CARGAR EL MODELO .rknn EN MEMORIA
# ─────────────────────────────────────────────────────────────────────────────
print()
print("PASO 2 — Cargando modelo...")

# RKNNLite es el objeto central: gestiona el ciclo de vida del modelo.
# Piénselo como un "motor de inferencia" que todavía no está encendido.
rknn = RKNNLite()

# load_rknn() lee el archivo binario .rknn del disco y lo deserializa en RAM.
# En este punto el NPU aún NO está involucrado; esto es trabajo de la CPU.
# Retorna 0 si todo está bien, valor negativo si hay error.
t_inicio = time.perf_counter()
ret = rknn.load_rknn(ARCHIVO_MODELO)
t_carga = time.perf_counter() - t_inicio

if ret != 0:
    print(f"  ✗ load_rknn() falló con código {ret}.")
    print(f"    Verifique que '{ARCHIVO_MODELO}' no esté corrupto.")
    print(f"    Elimínelo y vuelva a ejecutar para descargarlo de nuevo.")
    sys.exit(1)

print(f"  ✓ Modelo cargado en {t_carga * 1000:.1f} ms  (lectura de disco + deserialización)")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3 — INICIALIZAR EL DRIVER DEL NPU
# ─────────────────────────────────────────────────────────────────────────────
print()
print("PASO 3 — Inicializando el NPU...")

# init_runtime() es cuando el NPU se "enciende":
#   1. El driver rknpu reserva buffers DMA en memoria física
#   2. Carga el grafo de computación en la SRAM interna del NPU
#   3. Configura los registros del acelerador
#
# IMPORTANTE: load_rknn() DEBE llamarse antes. init_runtime() necesita conocer
# la arquitectura del modelo (formas de tensores, operaciones) para dimensionar
# los buffers correctamente. Sin esta información retorna -1.
#
# Nota sobre los mensajes de dmesg:
#   Al arrancar, el kernel imprime "RKNPU: can't request region for resource".
#   Esto es un defecto conocido del BSP 5.10 y NO impide que la NPU funcione.

t_inicio = time.perf_counter()
ret = rknn.init_runtime()
t_init = time.perf_counter() - t_inicio

if ret != 0:
    print(f"  ✗ init_runtime() falló con código {ret}.")
    print("    Posibles causas:")
    print("      - El módulo rknpu no está cargado (ejecute setup_npu.sh)")
    print("      - librknnrt.so no está en LD_LIBRARY_PATH")
    rknn.release()
    sys.exit(1)

print(f"  ✓ NPU inicializado en {t_init * 1000:.1f} ms")
print("    (Esta inicialización ocurre una vez; las inferencias sucesivas son más rápidas)")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4 — PREPROCESAR LA IMAGEN → TENSOR DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────
print()
print("PASO 4 — Preparando tensor de entrada...")

# ¿Qué es un tensor?
# Un tensor es un arreglo multidimensional de números. Para una imagen RGB de
# 224×224 píxeles, el tensor tiene forma (altura, ancho, canales) = (224, 224, 3).
# "Canales" son los tres planos de color: Rojo, Verde, Azul.

imagen_bgr = cv2.imread(ARCHIVO_IMAGEN)

# cv2.imread() retorna None si el archivo no se puede leer (corrupto, permisos, etc.)
if imagen_bgr is None:
    print(f"  ✗ No se pudo leer '{ARCHIVO_IMAGEN}'.")
    print("    El archivo puede estar corrupto. Elimínelo y vuelva a ejecutar.")
    rknn.release()
    sys.exit(1)

# ¿Por qué convertir BGR → RGB?
# OpenCV (cv2) carga imágenes en orden BGR (Azul-Verde-Rojo) por razones históricas.
# ResNet-18 fue entrenado con imágenes en orden RGB (Rojo-Verde-Azul).
# Si no se convierte, el modelo interpreta el canal Rojo como Azul y viceversa,
# degradando significativamente la precisión.
imagen_rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)

# ¿Por qué expand_dims?
# La red espera un LOTE (batch) de imágenes como entrada, no una sola imagen.
# La convención es (N, H, W, C): lote, altura, ancho, canales.
# Con una sola imagen: N=1, H=224, W=224, C=3.
# expand_dims agrega la dimensión del lote: (224, 224, 3) → (1, 224, 224, 3)
tensor = np.expand_dims(imagen_rgb, axis=0)

print(f"  ✓ Imagen leída: {imagen_bgr.shape[1]}×{imagen_bgr.shape[0]} px")
print(f"  ✓ Tensor de entrada: forma {tensor.shape}, tipo {tensor.dtype}")
print(f"    Interpretación: {tensor.shape[0]} imagen(es), "
      f"{tensor.shape[1]}×{tensor.shape[2]} px, {tensor.shape[3]} canales RGB")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 5 — EJECUTAR INFERENCIA EN EL NPU Y MEDIR TIEMPO
# ─────────────────────────────────────────────────────────────────────────────
print()
print("PASO 5 — Ejecutando inferencia en el NPU...")

try:
    # Primera inferencia: puede ser más lenta por la compilación JIT del grafo
    t_inicio = time.perf_counter()
    salidas = rknn.inference(inputs=[tensor])
    t_inferencia_1 = (time.perf_counter() - t_inicio) * 1000

    # Segunda inferencia: mide el tiempo estable (sin overhead de inicialización)
    t_inicio = time.perf_counter()
    salidas = rknn.inference(inputs=[tensor])
    t_inferencia_2 = (time.perf_counter() - t_inicio) * 1000

    print(f"  ✓ Primera inferencia : {t_inferencia_1:.1f} ms  (incluye compilación JIT)")
    print(f"  ✓ Segunda inferencia : {t_inferencia_2:.1f} ms  (tiempo estable)")

finally:
    # release() siempre se ejecuta, incluso si inference() lanza una excepción.
    # Libera los buffers DMA y cierra el descriptor del driver rknpu.
    # Sin esto, el driver retiene memoria hasta que el proceso termina.
    rknn.release()


# ─────────────────────────────────────────────────────────────────────────────
# PASO 6 — INTERPRETAR EL VECTOR DE SALIDA
# ─────────────────────────────────────────────────────────────────────────────
print()
print("PASO 6 — Interpretando resultados...")

# salidas es una lista de arrays NumPy, uno por cada tensor de salida del modelo.
# ResNet-18 tiene un único tensor de salida de forma (1, 1000):
#   - 1: tamaño del lote
#   - 1000: una puntuación (logit) por cada clase de ImageNet
vector_salida = salidas[0][0]   # extraer el vector 1D de 1000 elementos

print(f"  Vector de salida: {len(vector_salida)} valores (uno por clase ImageNet)")
print(f"  Rango de logits: [{vector_salida.min():.2f}, {vector_salida.max():.2f}]")

# Top-K: los K índices con mayor puntuación, ordenados de mayor a menor.
# argsort() ordena de menor a mayor; con [::-1] se invierte el orden.
indices_top_k = np.argsort(vector_salida)[::-1][:TOP_K]

print()
print(f"  ┌── Top-{TOP_K} clasificaciones ──────────────────────────────────┐")
for posicion, indice in enumerate(indices_top_k, start=1):
    logit = vector_salida[indice]
    nombre = nombre_clase(indice)
    indicador = " ← CORRECTO" if indice == 812 else ""
    print(f"  │  {posicion}. [{indice:4d}] {nombre:<28} logit={logit:7.2f}{indicador}")
print(f"  └─────────────────────────────────────────────────────────────┘")


# ─────────────────────────────────────────────────────────────────────────────
# [AVANZADO] APLICAR SOFTMAX PARA OBTENER PROBABILIDADES REALES
# ─────────────────────────────────────────────────────────────────────────────
print()
print("[AVANZADO] Probabilidades tras aplicar softmax:")
print()

# Los logits no se pueden comparar directamente entre imágenes porque su escala
# depende del modelo y de la entrada. Softmax los transforma en probabilidades:
# valores entre 0 y 1 que suman exactamente 1, interpretables como confianza.
probabilidades = aplicar_softmax(vector_salida)
indices_top_k_prob = np.argsort(probabilidades)[::-1][:TOP_K]

print(f"  ┌── Top-{TOP_K} con softmax ────────────────────────────────────────┐")
for posicion, indice in enumerate(indices_top_k_prob, start=1):
    prob  = probabilidades[indice] * 100
    barra = "█" * int(prob / 2) + "░" * (50 - int(prob / 2))
    nombre = nombre_clase(indice)
    print(f"  │  {posicion}. [{indice:4d}] {nombre:<22} {prob:6.2f}%  {barra[:20]}")
print(f"  └─────────────────────────────────────────────────────────────┘")
print()
print("  Nota: si la probabilidad de la clase correcta es < 50%, el modelo")
print("  está en duda. Si es < 10%, la imagen no se parece a ninguna clase")
print("  conocida del conjunto de entrenamiento de ImageNet.")


# ─────────────────────────────────────────────────────────────────────────────
# [AVANZADO] RENDIMIENTO SOSTENIDO: N INFERENCIAS CONSECUTIVAS
# ─────────────────────────────────────────────────────────────────────────────
print()
print("[AVANZADO] Midiendo rendimiento sostenido (20 inferencias)...")
print("  (Para esto se necesita reinicializar el NPU)")
print()

N_ITER = 20
rknn2 = RKNNLite()
rknn2.load_rknn(ARCHIVO_MODELO)
rknn2.init_runtime()

tiempos = []
try:
    for _ in range(N_ITER):
        t0 = time.perf_counter()
        rknn2.inference(inputs=[tensor])
        tiempos.append((time.perf_counter() - t0) * 1000)
finally:
    rknn2.release()

t_media  = sum(tiempos) / len(tiempos)
t_minimo = min(tiempos)
t_maximo = max(tiempos)
fps      = 1000 / t_media

print(f"  Resultados sobre {N_ITER} inferencias:")
print(f"    Tiempo medio  : {t_media:.1f} ms")
print(f"    Tiempo mínimo : {t_minimo:.1f} ms")
print(f"    Tiempo máximo : {t_maximo:.1f} ms")
print(f"    Rendimiento   : {fps:.1f} imágenes/segundo")
print()
print("  Referencia:")
print("    NPU RK3588 (INT8)   ~5–15 ms  →  ~70–200 FPS")
print("    CPU Cortex-A76      ~400 ms   →  ~2.5 FPS")
print("    GPU Mali-G610       ~30 ms    →  ~33 FPS  (OpenCL, si disponible)")


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 65)
print("  RESUMEN")
print("=" * 65)
clase_predicha = int(np.argmax(vector_salida))
print(f"  Clase predicha  : {clase_predicha} ({nombre_clase(clase_predicha)})")
print(f"  Resultado       : {'CORRECTO (clase 812 = space shuttle)' if clase_predicha == 812 else 'INCORRECTO'}")
print(f"  Inferencia NPU  : {t_inferencia_2:.1f} ms  ({1000/t_inferencia_2:.0f} FPS)")
print()
print("  PRÓXIMOS PASOS PARA SEGUIR APRENDIENDO:")
print("  1. Cambie ARCHIVO_IMAGEN por otra foto propia y vea qué predice")
print("  2. Pruebe con un modelo YOLOv5 (detección de objetos con bounding boxes)")
print("  3. Use rknn-toolkit2 en un PC para compilar su propio modelo ONNX")
print("  4. Ejecute inferencias en los 3 núcleos NPU en paralelo con threads")
print("=" * 65)
