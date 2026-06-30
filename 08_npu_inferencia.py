"""
Módulo 8 — Inferencia de redes neuronales en el NPU RK3588
===========================================================

Objetivo de aprendizaje
-----------------------
Comprender la arquitectura del procesador neuronal (NPU) integrado en el
RK3588, el ecosistema de software RKNN y el flujo completo de inferencia
desde la carga del modelo hasta la interpretación del vector de salida.

Marco teórico
-------------
Unidad de Procesamiento Neuronal (NPU)
    El RK3588 integra una NPU de tres núcleos de 2 TOPS cada uno, para
    un rendimiento total de 6 TOPS (tera-operaciones por segundo, medidos
    con operaciones enteras de 8 bits, INT8). Esta unidad está optimizada
    para inferencia de redes neuronales convolucionales (CNN), con soporte
    para las operaciones más comunes: convolución, normalización, pooling,
    activación y multiplicación matricial.

    La NPU opera de forma completamente independiente de la CPU y la GPU,
    consumiendo su propio banco de energía y accediendo a DRAM mediante un
    controlador DMA dedicado.

Ecosistema RKNN
    Rockchip define dos herramientas complementarias:

    rknn-toolkit2 (PC, x86-64 únicamente)
        Convierte modelos de PyTorch, TensorFlow, ONNX, Caffe y otros
        formatos al binario .rknn. Aplica cuantización post-entrenamiento
        (INT8 o INT16) para maximizar el rendimiento en la NPU.

    rknn-toolkit-lite2 (placa ARM)
        Carga modelos .rknn y ejecuta inferencia utilizando el driver del
        kernel (módulo rknpu). No tiene capacidad de conversión.

Flujo de inferencia y orden de operaciones
------------------------------------------
    rknn = RKNNLite()
    rknn.load_rknn(ruta)      # Deserializa el modelo en RAM del sistema
    rknn.init_runtime()       # Inicializa el driver rknpu y asigna buffers
                              # DEBE invocarse DESPUÉS de load_rknn().
                              # Antes de cargar el modelo, init_runtime()
                              # no puede dimensionar los buffers de entrada/
                              # salida → retorna código de error -1.
    rknn.inference(inputs=[]) # Transfiere tensores a la NPU, ejecuta y
                              # retorna los tensores de salida.
    rknn.release()            # Libera buffers y descriptores del driver.

Sobre los mensajes de error en dmesg
--------------------------------------
Al arrancar, el kernel BSP del RK3588 imprime:

    RKNPU: can't request region for resource [mem ...]
    failed to initialize power model

Esto es un defecto conocido del árbol de código vendor (BSP 5.10) que no
afecta la funcionalidad de la NPU. La inferencia opera con normalidad
pese a estos mensajes.

Modelo de prueba
----------------
ResNet-18 es una red convolucional profunda de 18 capas entrenada sobre
ImageNet (1000 clases). El modelo incluido en este módulo fue compilado
por el equipo de Rockchip para el RK3588 con cuantización INT8 y
optimizaciones de layout de memoria específicas para la NPU.

Prerrequisitos del sistema
--------------------------
    Haber ejecutado setup_npu.sh.
    Dependencias: pip3 install rknn-toolkit-lite2 opencv-python numpy
    La primera ejecución descarga el modelo y la imagen (~12 MB).

Uso
---
    python3 08_npu_inferencia.py
"""

import os
import urllib.request

import cv2
import numpy as np
from rknnlite.api import RKNNLite

REPO  = ("https://raw.githubusercontent.com/airockchip/"
          "rknn-toolkit2/master/rknn-toolkit-lite2/examples/resnet18")
MODELO = "resnet18_for_rk3588.rknn"
IMAGEN = "space_shuttle_224.jpg"


def descargar_si_falta(nombre: str, url: str) -> None:
    if not os.path.exists(nombre):
        print(f"  Descargando {nombre} ...")
        try:
            urllib.request.urlretrieve(url, nombre)
        except Exception as e:
            # Eliminar archivo parcial para que el siguiente intento descargue completo
            if os.path.exists(nombre):
                os.remove(nombre)
            raise RuntimeError(f"Error al descargar {nombre}: {e}") from e
        print(f"  {os.path.getsize(nombre) / 1e6:.1f} MB descargados.")


print("=== Inferencia de imagen en el NPU RK3588 ===\n")

print("1. Verificando archivos necesarios...")
descargar_si_falta(MODELO, f"{REPO}/{MODELO}")
descargar_si_falta(IMAGEN, f"{REPO}/{IMAGEN}")

rknn = RKNNLite()

try:
    print("2. Cargando modelo ResNet-18 compilado para RK3588...")
    ret = rknn.load_rknn(MODELO)
    if ret != 0:
        raise RuntimeError(
            f"load_rknn() retornó código {ret}.\n"
            f"Verifique que el archivo '{MODELO}' exista y no esté corrupto."
        )

    print("3. Inicializando runtime del NPU (rknpu)...")
    ret = rknn.init_runtime()
    if ret != 0:
        raise RuntimeError(
            f"init_runtime() retornó código {ret}.\n"
            "Verifique que el módulo rknpu esté cargado:\n"
            "    lsmod | grep rknpu"
        )
    print("   Runtime inicializado correctamente.")

    print("4. Preparando tensor de entrada...")
    imagen_bgr = cv2.imread(IMAGEN)
    if imagen_bgr is None:
        raise RuntimeError(
            f"cv2.imread() no pudo leer '{IMAGEN}'.\n"
            "El archivo puede estar corrupto. Elimínelo y vuelva a ejecutar."
        )
    imagen_rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)
    tensor     = np.expand_dims(imagen_rgb, axis=0)   # → forma [1, 224, 224, 3]
    print(f"   Tensor: forma {tensor.shape}, dtype {tensor.dtype}")

    print("5. Ejecutando inferencia en el NPU...")
    salidas = rknn.inference(inputs=[tensor])

    clase   = int(np.argmax(salidas[0]))
    puntaje = float(salidas[0][0][clase])

    print()
    print("=== Resultado ===")
    print(f"  Clase predicha (índice ImageNet) : {clase}")
    print(f"  Puntaje de confianza             : {puntaje:.4f}")
    print(f"  Clase 812 en ImageNet            : 'space shuttle'")
    print(f"  Clasificación {'correcta' if clase == 812 else 'incorrecta'}.")

finally:
    # Siempre liberar recursos del driver, incluso si ocurrió una excepción
    rknn.release()
