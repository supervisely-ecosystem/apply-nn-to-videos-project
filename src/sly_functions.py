
@sly.timeit
def init(data, state):
    state["activeStep"] = 1
    state["restartFrom"] = None

    input_project.init(data, state)  # 1 stage
    connect_to_model.init(data, state)  # 2 stage
    choose_classes.init(data, state)  # 3 stage
    choose_videos.init(data, state)  # 4 stage
    parameters.init(data, state)  # 5 stage
    output_data.init(data, state)  # 6 stage


@g.my_app.callback("restart")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def restart(api: sly.Api, task_id, context, state, app_logger):
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
