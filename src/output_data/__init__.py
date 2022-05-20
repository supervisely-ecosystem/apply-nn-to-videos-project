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

init_progress("Videos", data)

data['dstProjectId'] = None
data['dstProjectName'] = None
data['dstProjectPreviewUrl'] = None

state["annotatingStarted"] = False

state["collapsed6"] = True
state["disabled6"] = True
data["done6"] = False
