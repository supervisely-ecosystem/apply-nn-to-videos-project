from pathlib import Path

from jinja2 import Environment

from supervisely.app import StateJson, DataJson

import src.sly_globals as g

from src.output_data.handlers import *
from src.output_data.functions import *
from src.output_data.widgets import *


##############
# init fields
##############


DataJson()['dstProjectId'] = None
DataJson()['dstProjectName'] = None
DataJson()['dstProjectPreviewUrl'] = None

StateJson()["annotatingStarted"] = False

StateJson()["collapsed6"] = True
StateJson()["disabled6"] = True
DataJson()["done6"] = False
