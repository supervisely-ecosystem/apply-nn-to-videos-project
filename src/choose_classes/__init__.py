from pathlib import Path

from jinja2 import Environment

from supervisely.app import StateJson, DataJson

import src.sly_globals as g

from src.example_card.handlers import *
from src.example_card.functions import *
from src.example_card.widgets import *


data["classesTable"] = []

state["selectedClasses"] = []

data["done3"] = False
state["collapsed3"] = True
state["disabled3"] = True
