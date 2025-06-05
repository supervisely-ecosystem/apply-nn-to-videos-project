import os
import uvicorn
import yaml

import random
import supervisely as sly
from fastapi import Depends
from starlette.requests import Request
from supervisely.app import StateJson

import src.sly_globals as g
from src.ui import layout

app = sly.Application(
    layout=layout,
    static_dir=os.path.join(g.app_root_directory, "static"),
    show_header=False
)
server = app.get_server()


@server.post("/apply_changes/")
async def apply_changes(state: StateJson = Depends(StateJson.from_request)):
    await state.synchronize_changes()


import src.handlers
import src.functions
