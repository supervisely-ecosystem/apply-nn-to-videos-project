from fastapi import Depends

import supervisely
from supervisely import logger


@g.my_app.post("choose_classes")
@sly.timeit
def choose_videos(api: sly.api, task_id, context, state, app_logger):
    selected_count = len(state['selectedClasses'])

    if selected_count == 0:
        raise ValueError('No classes selected. Please select one class at least .')

    # g.finish_step(3)
    step_num = 3 # temp solution
    next_step = 5 # temp solution

    fields = [ # temp solution
        {"field": f"data.done{step_num}", "payload": True},
        {"field": f"state.collapsed{next_step}", "payload": False},
        {"field": f"state.disabled{next_step}", "payload": False},
        {"field": f"state.activeStep", "payload": 4},
    ]
    api.app.set_field(task_id, "data.scrollIntoView", f"step{4}")
    api.app.set_fields(task_id, fields)

