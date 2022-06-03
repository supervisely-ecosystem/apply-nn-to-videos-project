from pathlib import Path

from jinja2 import Environment

from supervisely.app import StateJson, DataJson

import src.sly_globals as g

from src.parameters.handlers import *
from src.parameters.functions import *
from src.parameters.widgets import *


##############
# init fields
##############

# system
StateJson()["expId"] = f"{g.project_info.name}(inf)"
StateJson()["confThres"] = 0.4
DataJson()["previewLoading"] = False

StateJson()['modelSettings'] = ""

# stepper
DataJson()["videoUrl"] = None

StateJson()["collapsed5"] = True
StateJson()["disabled5"] = True
DataJson()["done5"] = False

