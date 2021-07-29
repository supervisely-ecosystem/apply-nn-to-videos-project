
import yaml

import random
import supervisely_lib as sly
import ui.ui as ui

import sly_globals as g




@g.my_app.callback("select_all_classes")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def select_all_classes(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.classes", [True] * len(model_meta.obj_classes))


@g.my_app.callback("deselect_all_classes")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def deselect_all_classes(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.classes", [False] * len(model_meta.obj_classes))


@g.my_app.callback("select_all_tags")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def select_all_tags(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.tags", [True] * len(model_meta.tag_metas))


@g.my_app.callback("deselect_all_tags")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def deselect_all_tags(api: sly.Api, task_id, context, state, app_logger):
    api.task.set_field(task_id, "state.tags", [False] * len(model_meta.tag_metas))


@g.my_app.callback("preview")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def preview(api: sly.Api, task_id, context, state, app_logger):
    pass


@g.my_app.callback("apply_model")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def apply_model(api: sly.Api, task_id, context, state, app_logger):
   pass


def main():
    data = {}
    state = {}
    data["ownerId"] = g.owner_id
    data["teamId"] = g.team_id

    g.my_app.compile_template(g.root_source_path)

    ui.init(data, state)

    g.my_app.run(data=data, state=state)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
