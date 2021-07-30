import os

import supervisely_lib as sly
import sly_globals as g
from sly_progress import get_progress_cb, reset_progress, init_progress

from choose_videos import fill_table as fill_videos_table  # temp solution
from choose_videos import generate_rows as generate_videos_rows  # temp solution

import cv2


def init(data, state):
    data["projectId"] = g.project_info.id
    data["projectName"] = g.project_info.name
    data["projectItemsCount"] = g.project_info.items_count
    data["projectPreviewUrl"] = g.api.image.preview_url(g.project_info.reference_image_url, 100, 100)

    init_progress("InputProject", data)

    state['inputLoading'] = False

    data["done1"] = False
    state["collapsed1"] = False

    data['videosData'] = []


@g.my_app.callback("select_projects_handler")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def select_projects_handler(api: sly.api, task_id, context, state, app_logger):
    rows = generate_videos_rows([g.project_id])  # temp solution
    fill_videos_table(rows)  # temp solution

    g.finish_step(1)


