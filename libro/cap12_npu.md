# Capítulo 12 — Inteligencia Artificial en el Edge con la NPU

## Objetivo

Al finalizar este capítulo el lector ejecutará modelos de redes neuronales en el NPU del RK3588, comprenderá el proceso de conversión de modelos al formato RKNN y desplegará un pipeline de visión por computador en tiempo real.

**Archivos de código:** `08_npu_inferencia.py`

---

## 12.1 Fundamentos de redes neuronales para visión

### ¿Qué es una red neuronal convolucional (CNN)?

Una CNN es un tipo de red neuronal diseñada para procesar datos con estructura espacial (imágenes). Su arquitectura apila tres tipos de capas:

```
Imagen de entrada (224×224×3 píxeles)
        ↓
┌─────────────────────────────────┐
│  Capas Convolucionales           │  → detectan bordes, texturas, formas
│  Conv → BatchNorm → ReLU         │
└───────────────┬─────────────────┘
                ↓
┌─────────────────────────────────┐
│  Capas de Pooling                │  → reducen resolución espacial
│  MaxPool / AvgPool               │
└───────────────┬─────────────────┘
                ↓
┌─────────────────────────────────┐
│  Capas Completamente Conectadas  │  → clasificación final
│  Linear → Softmax                │
└───────────────┬─────────────────┘
                ↓
Vector de 1000 probabilidades (una por clase ImageNet)
```

### ¿Qué es ImageNet?

ImageNet es el conjunto de datos de referencia en clasificación de imágenes: 1.28 millones de imágenes de entrenamiento distribuidas en 1000 clases (animales, vehículos, objetos cotidianos, etc.). Un modelo que alcanza >75% de precisión Top-1 en ImageNet se considera competitivo.

### ResNet-18: la arquitectura del modelo de prueba

ResNet-18 fue propuesto por Microsoft Research en 2015. Sus 18 capas incluyen **conexiones residuales**: cada bloque puede "saltarse" a sí mismo, lo que permite entrenar redes más profundas sin el problema del desvanecimiento del gradiente.

```
Entrada
   ↓
[Conv 7×7, 64 filtros, stride=2]
   ↓
[MaxPool, stride=2]
   ↓
[Bloque residual 1] × 2
   ↓
[Bloque residual 2] × 2
   ↓
[Bloque residual 3] × 2
   ↓
[Bloque residual 4] × 2
   ↓
[GlobalAvgPool]
   ↓
[Linear, 1000 salidas]
   ↓
Logits (1000 valores)
```

---

## 12.2 El NPU del RK3588: arquitectura de hardware

### Array sistólico

El núcleo computacional del NPU es un **array sistólico**: una cuadrícula 2D de unidades multiply-accumulate (MAC) donde los datos fluyen de forma sincronizada entre celdas adyacentes, sin acceder a memoria en cada operación.

```
Flujo de datos →
        ┌───┬───┬───┬───┐
        │MAC│MAC│MAC│MAC│
Pesos ↓ ├───┼───┼───┼───┤
        │MAC│MAC│MAC│MAC│
        ├───┼───┼───┼───┤
        │MAC│MAC│MAC│MAC│
        └───┴───┴───┴───┘
```

Esto permite alta eficiencia energética porque los datos se reutilizan localmente en lugar de ir a DRAM en cada operación.

### Cuantización INT8

Los modelos de red neuronal típicamente se entrenan con pesos en punto flotante de 32 bits (FP32). La cuantización los convierte a enteros de 8 bits (INT8):

| Formato | Bits por parámetro | Precisión relativa | Rendimiento NPU |
|---|---|---|---|
| FP32 | 32 | Línea base | No compatible |
| FP16 | 16 | ~99.5% | Compatible |
| INT8 | 8 | ~98–99% | Máximo (6 TOPS) |
| INT4 | 4 | ~95–98% | Compatible (3 TOPS) |

La cuantización post-entrenamiento requiere un dataset de calibración de ~100 imágenes para ajustar los rangos de cada capa.

---

## 12.3 El ecosistema RKNN

```
PC de desarrollo (x86-64)
┌──────────────────────────────────────────────────────┐
│  rknn-toolkit2                                       │
│                                                      │
│  ONNX / PyTorch / TensorFlow → .rknn                 │
│                                                      │
│  Pasos:                                              │
│    1. rknn.config(target_platform='rk3588')          │
│    2. rknn.load_onnx('modelo.onnx')                  │
│    3. rknn.build(do_quantization=True,               │
│                  dataset='calibracion.txt')           │
│    4. rknn.export_rknn('modelo_rk3588.rknn')         │
└──────────────────────────────────────────────────────┘
                 ↓ transferir .rknn
Orange Pi 5 Plus
┌──────────────────────────────────────────────────────┐
│  rknn-toolkit-lite2                                  │
│                                                      │
│    rknn = RKNNLite()                                 │
│    rknn.load_rknn('modelo_rk3588.rknn')              │
│    rknn.init_runtime()                               │
│    salidas = rknn.inference(inputs=[tensor])         │
│    rknn.release()                                    │
└──────────────────────────────────────────────────────┘
```

---

## 12.4 Módulo 8: inferencia con ResNet-18

**Archivo:** `08_npu_inferencia.py`

El módulo implementa el pipeline completo en 6 pasos documentados:

| Paso | Operación | Tiempo típico |
|---|---|---|
| 0 | Verificar dependencias | < 1 ms |
| 1 | Descargar modelo e imagen (primera vez) | ~30 s (red) |
| 2 | Cargar modelo `.rknn` desde disco | ~10 ms |
| 3 | Inicializar runtime del NPU | ~80 ms |
| 4 | Preprocesar imagen → tensor | ~2 ms |
| 5 | Ejecutar inferencia en el NPU | ~5 ms |
| 6 | Interpretar vector de salida (Top-5) | < 1 ms |

**Rendimiento medido en la Orange Pi 5 Plus:**
- Tiempo de inferencia estable: **4.9–5.5 ms** por imagen
- Rendimiento sostenido (20 iteraciones): **181 imágenes/segundo**

```bash
./setup_npu.sh
python3 08_npu_inferencia.py
```

---

## 12.5 Preprocesamiento de imágenes: por qué importa

El preprocesamiento incorrecto es la causa más común de clasificaciones erróneas, incluso con el modelo correcto.

### Conversión BGR → RGB

```python
imagen_bgr = cv2.imread("foto.jpg")   # OpenCV: Blue-Green-Red
imagen_rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)
```

ResNet-18 fue entrenado con imágenes en formato RGB. Si se pasa BGR, el modelo confunde el canal Rojo con el Azul, degradando la precisión.

### Redimensionado

```python
# ResNet-18 espera exactamente 224×224 píxeles
imagen_224 = cv2.resize(imagen_rgb, (224, 224))
```

Para mantener la proporción de aspecto al redimensionar:

```python
h, w = imagen_rgb.shape[:2]
escala = 224 / min(h, w)
imagen_scaled = cv2.resize(imagen_rgb, (int(w*escala), int(h*escala)))

# Centro crop
cy, cx = imagen_scaled.shape[:2]
y0 = (cy - 224) // 2
x0 = (cx - 224) // 2
imagen_224 = imagen_scaled[y0:y0+224, x0:x0+224]
```

### Normalización (para modelos no cuantizados)

Si el modelo espera entrada normalizada (común en FP32):

```python
mean = np.array([0.485, 0.456, 0.406])  # media de ImageNet
std  = np.array([0.229, 0.224, 0.225])  # desviación estándar de ImageNet

imagen_norm = (imagen_224 / 255.0 - mean) / std
```

Los modelos RKNN con cuantización INT8 generalmente esperan `uint8` [0–255] directamente; la normalización se aplica internamente.

---

## 12.6 Convertir tu propio modelo

### Desde PyTorch

```python
# En un PC con rknn-toolkit2 instalado
from rknn.api import RKNN
import torch
import torchvision

# 1. Exportar el modelo de PyTorch a ONNX
modelo = torchvision.models.mobilenet_v2(pretrained=True)
modelo.eval()

dummy = torch.randn(1, 3, 224, 224)
torch.onnx.export(modelo, dummy, "mobilenetv2.onnx",
                  input_names=["imagen"], output_names=["logits"],
                  opset_version=11)

# 2. Convertir ONNX a RKNN
rknn = RKNN(verbose=False)
rknn.config(
    target_platform="rk3588",
    mean_values=[[0.485*255, 0.456*255, 0.406*255]],
    std_values=[[0.229*255, 0.224*255, 0.225*255]],
)
rknn.load_onnx(model="mobilenetv2.onnx")

# 3. Cuantizar (requiere ~100 imágenes en calibracion.txt)
rknn.build(do_quantization=True, dataset="calibracion.txt")

# 4. Exportar
rknn.export_rknn("mobilenetv2_rk3588.rknn")
rknn.release()
```

### Modelos precompilados disponibles

El repositorio oficial `airockchip/rknn-toolkit2` incluye modelos ya compilados para RK3588:

| Modelo | Tarea | Modos |
|---|---|---|
| ResNet-18/50 | Clasificación | INT8 |
| MobileNetV2 | Clasificación | INT8 |
| YOLOv5s/m | Detección | INT8 |
| YOLOv8n | Detección | INT8 |
| DeepLabV3 | Segmentación | INT8 |
| PaddleOCR | OCR | INT8 |

---

## 12.7 Inferencia en tiempo real con cámara

```python
import cv2
import numpy as np
from rknnlite.api import RKNNLite
import os

os.environ.setdefault("RKNN_LOG_LEVEL", "0")

rknn = RKNNLite()
rknn.load_rknn("resnet18_for_rk3588.rknn")
rknn.init_runtime()

cam = cv2.VideoCapture(0)   # /dev/video0

try:
    while True:
        ret, frame = cam.read()
        if not ret:
            break

        # Preprocesar
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (224, 224))
        tensor = np.expand_dims(img, axis=0)

        # Inferencia
        salidas = rknn.inference(inputs=[tensor])
        clase = int(np.argmax(salidas[0]))
        conf  = float(salidas[0][0][clase])

        # Mostrar resultado sobre el frame
        texto = f"Clase: {clase}  Conf: {conf:.1f}"
        cv2.putText(frame, texto, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("NPU - ResNet18", frame)

        if cv2.waitKey(1) == ord('q'):
            break
finally:
    cam.release()
    cv2.destroyAllWindows()
    rknn.release()
```

---

## Resumen del capítulo

- El NPU del RK3588 ejecuta inferencia de CNN hasta 90× más rápido que la CPU con ~1/5 del consumo energético.
- El preprocesamiento correcto (BGR→RGB, resize, tipo de datos) es tan importante como el modelo.
- El ecosistema RKNN sigue el flujo: modelo original → rknn-toolkit2 (PC) → archivo .rknn → rknn-toolkit-lite2 (placa).
- La cuantización INT8 reduce la precisión menos del 1–2% mientras maximiza el rendimiento en el hardware.

## Ejercicios

1. Modifique `08_npu_inferencia.py` para procesar su propia foto. Asegúrese de hacer el redimensionado correcto. ¿Clasifica correctamente objetos del mundo real?
2. Descargue el modelo YOLOv5s precompilado para RK3588 del repositorio oficial. Modifique el módulo 8 para usarlo y dibujar los bounding boxes sobre la imagen.
3. Mida el rendimiento de inferencia de ResNet-18 en el NPU vs. en la CPU (usando la versión ONNX del modelo con OpenCV DNN). ¿Cuántas veces es más rápido el NPU?
