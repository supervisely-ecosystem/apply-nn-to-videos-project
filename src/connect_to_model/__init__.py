from pathlib import Path

from jinja2 import Environment
from supervisely.app import StateJson, DataJson

import src.sly_globals as g

from src.connect_to_model.handlers import *
from src.connect_to_model.functions import *
from src.connect_to_model.widgets import *


##############
# init fields
##############

StateJson()["connectionLoading"] = False

DataJson()["modelInfo"] = {}
DataJson()["connected"] = False
DataJson()["connectionError"] = ""

DataJson()["ssOptions"] = {
    "sessionTags": ["deployed_nn"],
    "showLabel": False,
    "size": "small"
}

DataJson()["done2"] = False

StateJson()["collapsed2"] = True
StateJson()["disabled2"] = True


StateJson()["applyTrackingAlgorithm"] = True

DataJson()['model_without_tracking'] = False

StateJson()["selectedTrackingAlgorithm"] = 'deepsort'
DataJson()["trackingAlgorithms"] = [
    {'label': 'Deep Sort', 'value': 'deepsort'},
]

