# =====================================================================
# PlantNova API | Imagen para Cloud Run
#
# El punto crítico es instalar PyTorch desde el índice de CPU. La
# versión de PyPI arrastra las bibliotecas de CUDA y produce una
# imagen de varios gigabytes que Cloud Run no puede aprovechar,
# porque no hay GPU disponible.
# =====================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # PyTorch abre un hilo por núcleo por defecto y compite consigo
    # mismo en contenedores pequeños. Se limita al número de vCPU.
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2

# libgomp1 lo requiere el runtime de PyTorch. opencv-python-headless
# evita tener que instalar las bibliotecas gráficas de OpenCV.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-torch.txt ./

# PyTorch va desde el índice de CPU y en su propio paso: la versión de
# PyPI arrastra las bibliotecas de CUDA, que en Cloud Run no sirven de
# nada y añaden gigabytes a la imagen.
RUN pip install --no-cache-dir -r requirements-torch.txt \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY models ./models

ENV PORT=8080

# Un solo worker: cada uno carga su propia copia del modelo en
# memoria. La concurrencia se controla desde Cloud Run.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
