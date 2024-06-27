from pathlib import Path

from jinja2 import Environment
from supervisely.app import DataJson, StateJson

import src.sly_globals as g


##############
# init fields
##############
DataJson()["videosTable"] = []
StateJson()["selectedVideos"] = []

StateJson()["statsLoaded"] = False
StateJson()["loadingStats"] = False

StateJson()["framesMin"] = {}
StateJson()["framesMax"] = {}

DataJson()["done4"] = False
StateJson()["collapsed4"] = True
StateJson()["disabled4"] = True

##############
# init routes
##############

# server.add_api_route('/some_post_request_from_frontend/', card_handlers.example_route, methods=["POST"])
