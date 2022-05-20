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
data["videosTable"] = []
state["selectedVideos"] = []

state["statsLoaded"] = False
state["loadingStats"] = False

state['framesMin'] = {}
state['framesMax'] = {}

data["done4"] = False
state["collapsed4"] = True
state["disabled4"] = True

##############
# init routes
##############

# g.app.add_api_route('/some_post_request_from_frontend/', card_handlers.example_route, methods=["POST"])


