FROM supervisely/base-pytorch:latest

RUN git clone https://github.com/supervisely-ecosystem/apply-nn-to-videos-project.git
RUN pip install -r apply-nn-to-videos-project/requirements.txt