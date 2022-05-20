from pathlib import Path

from jinja2 import Environment

from supervisely.app import StateJson, DataJson

import src.sly_globals as g

from src.example_card.handlers import *
from src.example_card.functions import *
from src.example_card.widgets import *


##############
# init fields
##############

# system
state["expId"] = f"{g.project_info.name}(inf)"
state["confThres"] = 0.4
state["previewLoading"] = False

# stepper
data["videoUrl"] = None

state["collapsed5"] = True
state["disabled5"] = True
data["done5"] = False