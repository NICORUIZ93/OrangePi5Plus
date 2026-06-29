#!/bin/bash
# Instala el runtime y toolkit del NPU (RK3588) para Python 3.10.
# Descarga directa de archivos puntuales del repo airockchip/rknn-toolkit2
# (no se clona el repo completo: pesa ~3.8GB).
set -e

REPO_RAW="https://raw.githubusercontent.com/airockchip/rknn-toolkit2/master"
WORKDIR=$(mktemp -d)
cd "$WORKDIR"

echo "Descargando wheel de rknn-toolkit-lite2 (Python 3.10)..."
curl -fL -o rknn_toolkit_lite2-2.3.2-cp310-cp310-linux_aarch64.whl \
  "$REPO_RAW/rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.3.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"

echo "Descargando librknnrt.so (runtime nativo aarch64)..."
curl -fL -o librknnrt.so \
  "$REPO_RAW/rknpu2/runtime/Linux/librknn_api/aarch64/librknnrt.so"

echo "Instalando paquete Python..."
pip3 install --user rknn_toolkit_lite2-2.3.2-cp310-cp310-linux_aarch64.whl

echo "Instalando librería del sistema (requiere sudo)..."
sudo cp librknnrt.so /usr/lib/
sudo ldconfig

echo "Verificando import..."
python3 -c "from rknnlite.api import RKNNLite; print('rknnlite OK')"

cd /
rm -rf "$WORKDIR"
echo "Listo. Para probar con un modelo real, descarga un .rknn compilado para rk3588"
echo "desde rknn-toolkit-lite2/examples/ del mismo repo."
