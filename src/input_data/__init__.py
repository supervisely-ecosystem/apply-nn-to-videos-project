from pathlib import Path

from jinja2 import Environment

from supervisely.app import StateJson, DataJson

import src.sly_globals as g

from src.input_data.handlers import *
from src.input_data.functions import *
from src.input_data.widgets import *


##############
# init fields
##############
DataJson()["projectId"] = g.project_info.id
DataJson()["projectName"] = g.project_info.name
DataJson()["projectItemsCount"] = g.project_info.items_count if g.project_info.items_count else 0
DataJson()["projectPreviewUrl"] = g.api.image.preview_url(g.project_info.reference_image_url, 100, 100)


StateJson()['inputLoading'] = False

DataJson()["done1"] = False
StateJson()["collapsed1"] = False

DataJson()['videosDataJson()'] = []

DataJson()["videosTable"] = []
StateJson()["selectedVideos"] = []

StateJson()["statsLoaded"] = False
StateJson()["loadingStats"] = False

StateJson()['framesMin'] = {}
StateJson()['framesMax'] = {}

DataJson()["done4"] = False
StateJson()["collapsed4"] = True
StateJson()["disabled4"] = True
