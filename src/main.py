
import yaml

import random
import supervisely as sly
from fastapi import Depends
from starlette.requests import Request
from supervisely.app import StateJson

import src.sly_globals as g


import src.input_data
import src.connect_to_model
import src.choose_classes
import src.parameters
import src.output_data


@g.app.get("/")
def read_index(request: Request):
    return g.templates_env.TemplateResponse('index.html', {'request': request})


@g.app.post("/apply_changes/")
async def apply_changes(state: StateJson = Depends(StateJson.from_request)):
    await state.synchronize_changes()
