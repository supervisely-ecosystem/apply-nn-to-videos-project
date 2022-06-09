from pathlib import Path

from jinja2 import Environment

from supervisely.app import StateJson, DataJson

import src.sly_globals as g

from src.choose_classes.handlers import *
from src.choose_classes.functions import *
from src.choose_classes.widgets import *


DataJson()["classesTable"] = []

StateJson()["selectedClasses"] = []

DataJson()["done3"] = False
StateJson()["collapsed3"] = True
StateJson()["disabled3"] = True
