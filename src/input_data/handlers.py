from fastapi import Depends

import supervisely as sly
from supervisely import logger


import src.choose_videos.functions as choose_videos_functions  # temp solution

import src.sly_globals as g
import src.sly_functions as f


@g.app.post("/select_projects_handler/")
@sly.timeit
def select_projects_handler(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    table_rows = choose_videos_functions.generate_rows([g.project_id])  # temp solution
    choose_videos_functions.fill_table(table_rows=table_rows, state=state)  # temp solution

    f.finish_step(step_num=1, state=state)
