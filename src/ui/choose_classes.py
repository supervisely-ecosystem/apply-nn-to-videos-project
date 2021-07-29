import supervisely_lib as sly
import sly_globals as g

import os
from functools import partial

from sly_progress import get_progress_cb, reset_progress, init_progress


def init(data, state):
    data["classesTable"] = []

    state["selectedClasses"] = []

    data["done3"] = False
    state["collapsed3"] = True
    state["disabled3"] = True


def restart(data, state):
    data['done3'] = False


def generate_rows():
    rows = []
    obj_classes = g.model_meta.obj_classes
    for obj_class in obj_classes:


        rows.append(
            {
                'label': f'{obj_class.name}',
                'shapeType': f'{obj_class.geometry_type.geometry_name()}',
                'color': f'{"#%02x%02x%02x" % tuple(obj_class.color)}',
            }
        )
    return rows


def fill_table(table_rows):
    fields = [
        {"field": f"data.classesTable", "payload": table_rows, "recursive": False},
    ]
    g.api.task.set_fields(g.task_id, fields)

    return 0


@g.my_app.callback("choose_classes")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def choose_videos(api: sly.api, task_id, context, state, app_logger):
    selected_count = len(state['selectedClasses'])

    if selected_count == 0:
        raise ValueError('No classes selected. Please select one class at least .')

    g.finish_step(3)
