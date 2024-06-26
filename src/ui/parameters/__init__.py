from pathlib import Path

import torch
from jinja2 import Environment

from supervisely.app import StateJson, DataJson

import src.sly_globals as g


##############
# init fields
##############

# system
StateJson()["expId"] = f"{g.project_info.name}_NN"

DataJson()["previewLoading"] = False


StateJson()["modelSettings"] = ""
StateJson()["device"] = (
    "cuda:0" if torch.cuda.is_available() and torch.cuda.device_count() > 0 else "cpu"
)


# stepper
DataJson()["videoUrl"] = None

StateJson()["collapsed5"] = True
StateJson()["disabled5"] = True
DataJson()["done5"] = False
