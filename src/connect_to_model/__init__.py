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

state["connectionLoading"] = False

data["modelInfo"] = {}
data["connected"] = False
data["connectionError"] = ""

data["ssOptions"] = {
    "sessionTags": ["deployed_nn"],
    "showLabel": False,
    "size": "small"
}

data["done2"] = False

state["collapsed2"] = True
state["disabled2"] = True


##############
# init routes
##############

g.app.add_api_route('/some_post_request_from_frontend/', card_handlers.example_route, methods=["POST"])


