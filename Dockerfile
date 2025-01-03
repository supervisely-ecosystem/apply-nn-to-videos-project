FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/src/tensorrt/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    git \
    curl \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libmagic-dev \
    libexiv2-dev

RUN ln -s /usr/bin/python3 /usr/bin/python \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch==2.2.1 \
    torchvision==0.17.1

RUN pip install --no-cache-dir \
    setuptools==69.5.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY dev_requirements.txt dev_requirements.txt
RUN pip install --no-cache-dir -r dev_requirements.txt
RUN python3 -c "from supervisely.nn.tracker import *"

RUN pip install gdown && \
    mkdir -p ~/.cache/supervisely/checkpoints/ && \
    gdown "https://drive.google.com/uc?id=112EMUfBPYeYg70w-syK6V6Mx8-Qb9Q1M" -O ~/.cache/supervisely/checkpoints/osnet_x1_0_msmt17.pt && \
    gdown "https://drive.google.com/uc?id=1UT3AxIaDvS2PdxzZmbkLmjtiqq7AIKCv" -O ~/.cache/supervisely/checkpoints/osnet_x0_5_msmt17.pt