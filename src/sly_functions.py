from fastapi import Depends

import supervisely as sly

import src.sly_globals as g
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync


@g.app.post("restart")
@sly.timeit
def restart(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    restart_from_step = state["restartFrom"]
    data = {}
    state = {}

    if restart_from_step <= 2:
        connect_to_model.init(data, state)

    if restart_from_step <= 3:
        if restart_from_step == 3:
            choose_classes.restart(data, state)
        else:
            choose_classes.init(data, state)
    if restart_from_step <= 4:
        if restart_from_step == 4:
            choose_videos.restart(data, state)
        else:
            choose_videos.init(data, state)
    if restart_from_step <= 5:
        if restart_from_step == 5:
            parameters.restart(data, state)
        else:
            parameters.init(data, state)
    if restart_from_step <= 6:
        if restart_from_step == 6:
            output_data.restart(data, state)
        else:
            output_data.init(data, state)

    fields = [
        {"field": "data", "payload": data, "append": True, "recursive": False},
        {"field": "state", "payload": state, "append": True, "recursive": False},
        {"field": "state.restartFrom", "payload": None},
        {"field": f"state.collapsed{restart_from_step}", "payload": False},
        {"field": f"state.disabled{restart_from_step}", "payload": False},
        {"field": "state.activeStep", "payload": restart_from_step},
    ]
    g.api.app.set_fields(g.task_id, fields)
    g.api.app.set_field(task_id, "data.scrollIntoView", f"step{restart_from_step}")


def get_files_paths(src_dir, extensions):
    files_paths = []
    for root, dirs, files in os.walk(src_dir):
        for extension in extensions:
            for file in files:
                if file.endswith(extension):
                    file_path = os.path.join(root, file)
                    files_paths.append(file_path)

    return files_paths


def finish_step(step_num, state):
    next_step = step_num + 1
    DataJson()[f'done{step_num}'] = True
    state[f'collapsed{next_step}'] = False
    state[f'disabled{next_step}'] = False
    state[f'activeStep'] = next_step

    run_sync(DataJson().synchronize_changes())
    run_sync(state.synchronize_changes())
