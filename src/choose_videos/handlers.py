from fastapi import Depends

import supervisely as sly
from supervisely import logger

import src.sly_globals as g

#
# @g.app.post("/load_videos_info/")
# @sly.timeit
# def load_videos_info(api: sly.api, task_id, context, state, app_logger):
#     rows = generate_rows([g.project_id])
#     fill_table(rows)
#
#
# @g.app.callback("choose_videos")
# @sly.timeit
# def choose_videos(api: sly.api, task_id, context, state, app_logger):
#     selected_count = len(state['selectedVideos'])
#
#     if selected_count == 0:
#         raise ValueError('No videos selected. Please select videos.')
#
#     g.finish_step(4)
