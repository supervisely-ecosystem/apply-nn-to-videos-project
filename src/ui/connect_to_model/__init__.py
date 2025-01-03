from pathlib import Path

from jinja2 import Environment
from supervisely.app import StateJson, DataJson

import src.sly_globals as g


##############
# init fields
##############

StateJson()["connectionLoading"] = False

DataJson()["modelInfo"] = {}
DataJson()["connected"] = False
DataJson()["connectionError"] = ""

DataJson()["ssOptions"] = {"sessionTags": ["deployed_nn"], "showLabel": False, "size": "small"}

DataJson()["done2"] = False

StateJson()["collapsed2"] = True
StateJson()["disabled2"] = True


StateJson()["applyTrackingAlgorithm"] = True

DataJson()["model_without_tracking"] = False

StateJson()["selectedTrackingAlgorithm"] = "boxmot"
DataJson()["trackingAlgorithms"] = [
    {"label": "Deep Sort", "value": "deepsort"},
    {"label": "BoT", "value": "bot"},
    {"label": "BoT-SORT (boxmot)", "value": "boxmot"},
]
