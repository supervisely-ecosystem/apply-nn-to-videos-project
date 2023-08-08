FROM supervisely/base-py-sdk:6.72.96

RUN pip install torch==1.7.1+cu110 torchvision==0.8.2+cu110 -f https://download.pytorch.org/whl/torch_stable.html
COPY dev_requirements.txt dev_requirements.txt
RUN pip install -r dev_requirements.txt
