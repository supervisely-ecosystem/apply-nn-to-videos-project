from pathlib import Path

from jinja2 import Environment

from supervisely.app import StateJson, DataJson

import src.sly_globals as g


DataJson()["classesTable"] = []

StateJson()["selectedClasses"] = []

DataJson()["done3"] = False
StateJson()["collapsed3"] = True
StateJson()["disabled3"] = True
