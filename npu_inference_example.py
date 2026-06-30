"""Corre una inferencia real en el NPU (6 TOPS) de la RK3588.

Descarga un modelo ResNet-18 ya compilado para rk3588 y una imagen de
prueba (la primera vez, ~12MB), y predice su clase de ImageNet usando el
hardware NPU directamente (no la CPU).

Requiere haber corrido setup_npu.sh una vez.
"""
import os
import urllib.request

import cv2
import numpy as np
from rknnlite.api import RKNNLite

REPO = "https://raw.githubusercontent.com/airockchip/rknn-toolkit2/master/rknn-toolkit-lite2/examples/resnet18"
MODEL_PATH = "resnet18_for_rk3588.rknn"
IMAGE_PATH = "space_shuttle_224.jpg"


def download_if_missing(path, url):
    if not os.path.exists(path):
        print(f"Descargando {path}...")
        urllib.request.urlretrieve(url, path)


download_if_missing(MODEL_PATH, f"{REPO}/{MODEL_PATH}")
download_if_missing(IMAGE_PATH, f"{REPO}/{IMAGE_PATH}")

rknn = RKNNLite()
print("Cargando modelo...")
rknn.load_rknn(MODEL_PATH)

print("Inicializando runtime del NPU...")
ret = rknn.init_runtime()
if ret != 0:
    raise RuntimeError(f"El NPU no respondió (init_runtime devolvió {ret})")

img = cv2.imread(IMAGE_PATH)
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
img = np.expand_dims(img, axis=0)

print("Corriendo inferencia en el NPU...")
outputs = rknn.inference(inputs=[img])
clase = int(np.argmax(outputs[0]))
score = float(outputs[0][0][clase])

print(f"\nClase predicha (índice ImageNet): {clase} (score {score:.2f})")
print("812 = 'space shuttle', que es justo lo que muestra la imagen de prueba.")

rknn.release()
