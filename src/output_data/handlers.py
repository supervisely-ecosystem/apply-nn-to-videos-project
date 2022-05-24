from fastapi import Depends

import supervisely as sly
from supervisely import logger

import src.sly_globals as g


@g.app.post("start_annotation")
@sly.timeit
def start_annotation(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    annotate_videos()

    fields = [
        {"field": "data.done6", "payload": True},
        {"field": "state.annotatingStarted", "payload": False},
    ]

    g.api.app.set_fields(g.task_id, fields)
