from fastapi import Depends

import supervisely
from supervisely import logger



@g.my_app.callback("select_projects_handler")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def select_projects_handler(api: sly.api, task_id, context, state, app_logger):
    rows = generate_videos_rows([g.project_id])  # temp solution
    fill_videos_table(rows)  # temp solution

    g.finish_step(1)
