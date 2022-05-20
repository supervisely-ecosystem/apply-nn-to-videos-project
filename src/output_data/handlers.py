from fastapi import Depends

import supervisely
from supervisely import logger


@g.my_app.callback("start_annotation")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def start_annotation(api: sly.Api, task_id, context, state, app_logger):
    annotate_videos()

    fields = [
        {"field": "data.done6", "payload": True},
        {"field": "state.annotatingStarted", "payload": False},
    ]

    g.api.app.set_fields(g.task_id, fields)
