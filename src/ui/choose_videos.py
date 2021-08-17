import supervisely_lib as sly
import sly_globals as g


import os
from functools import partial

from sly_progress import get_progress_cb, reset_progress, init_progress


def init(data, state):
    data["videosTable"] = []

    state["statsLoaded"] = False
    state["loadingStats"] = False
    state["selectedVideos"] = []

    state['framesMin'] = {}
    state['framesMax'] = {}

    data["done4"] = False
    state["collapsed4"] = True
    state["disabled4"] = True
    
    rows = generate_rows([g.project_id])  # hardcoded
    fill_table(rows)  # hardcoded


def restart(data, state):
    data['done4'] = False


def get_videos_info(project_id):
    general_videos_info = []
    frames_min = {}
    frames_max = {}

    ds_ids = g.api.dataset.get_list(project_id)
    for ds_id in ds_ids:
        videos_info = g.api.video.get_list(ds_id.id)

        for video_info in videos_info:
            general_videos_info.append(
                {'name': f"[{ds_id.name}] {video_info.name}",
                 "dataset": ds_id.name,
                 "framesCount": video_info.frames_count,
                 "framesRange": "-",

                 "isDisabled": True if video_info.frames_count < 5 else False,

                 'videoId': video_info.id,
                 'videoHash': video_info.hash
                 }
            )

            frames_min[f"[{ds_id.name}] {video_info.name}"] = 0
            frames_max[f"[{ds_id.name}] {video_info.name}"] = video_info.frames_count - 1

    fields = [
        {"field": f"state.framesMin", "payload": frames_min},
        {"field": f"state.framesMax", "payload": frames_max},
    ]
    g.api.task.set_fields(g.task_id, fields)

    return general_videos_info


def generate_rows(project_ids):
    rows = []
    for project_id in project_ids:
        rows.extend(get_videos_info(project_id))

    return rows


def fill_table(table_rows):
    selected_videos = [row['name'] for row in table_rows if not row['isDisabled']] #@TODO: all selected in table
    fields = [
        {"field": f"state.statsLoaded", "payload": True},
        {"field": f"state.selectedVideos", "payload": selected_videos},
        {"field": f"data.videosTable", "payload": table_rows, "recursive": False},
    ]
    g.api.task.set_fields(g.task_id, fields)

    return 0


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
