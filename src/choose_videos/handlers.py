from fastapi import Depends

import supervisely
from supervisely import logger



@g.my_app.callback("load_videos_info")
@sly.timeit
# @g.my_app.ignore_errors_and_show_dialog_window()
def load_videos_info(api: sly.api, task_id, context, state, app_logger):
    rows = generate_rows([g.project_id])
    fill_table(rows)


@g.my_app.callback("choose_videos")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def choose_videos(api: sly.api, task_id, context, state, app_logger):
    selected_count = len(state['selectedVideos'])

    if selected_count == 0:
        raise ValueError('No videos selected. Please select videos.')

    g.finish_step(4)
