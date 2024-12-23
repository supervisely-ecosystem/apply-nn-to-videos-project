FROM supervisely/base-py-sdk:6.72.96

RUN pip install torch==2.2.1 torchvision==0.17.1 --index-url https://download.pytorch.org/whl/cu121
COPY dev_requirements.txt dev_requirements.txt
RUN pip install -r dev_requirements.txt
RUN python3 -c "from supervisely.nn.tracker import *"

RUN pip install gdown && \
    mkdir -p ~/.cache/supervisely/checkpoints/ && \
    gdown "https://drive.google.com/uc?id=112EMUfBPYeYg70w-syK6V6Mx8-Qb9Q1M" -O ~/.cache/supervisely/checkpoints/osnet_x1_0_msmt17.pt && \
    gdown "https://drive.google.com/uc?id=1UT3AxIaDvS2PdxzZmbkLmjtiqq7AIKCv" -O ~/.cache/supervisely/checkpoints/osnet_x0_5_msmt17.pt