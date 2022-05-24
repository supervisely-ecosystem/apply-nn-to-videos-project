from fastapi import Depends

import supervisely as sly
from supervisely import logger

import src.sly_globals as g


@g.app.post("/select_projects_handler/")
@sly.timeit
def select_projects_handler(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    rows = generate_videos_rows([g.project_id])  # temp solution
    fill_videos_table(rows)  # temp solution

    g.finish_step(1)
