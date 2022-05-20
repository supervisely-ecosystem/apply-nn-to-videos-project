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
data["projectId"] = g.project_info.id
data["projectName"] = g.project_info.name
data["projectItemsCount"] = g.project_info.items_count if g.project_info.items_count else 0
data["projectPreviewUrl"] = g.api.image.preview_url(g.project_info.reference_image_url, 100, 100)

init_progress("InputProject", data)

state['inputLoading'] = False

data["done1"] = False
state["collapsed1"] = False

data['videosData'] = []

data["videosTable"] = []
state["selectedVideos"] = []

state["statsLoaded"] = False
state["loadingStats"] = False

state['framesMin'] = {}
state['framesMax'] = {}

data["done4"] = False
state["collapsed4"] = True
state["disabled4"] = True
