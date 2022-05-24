import os
import sys
import pathlib
import supervisely as sly

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from supervisely.app import DataJson, StateJson
from supervisely.app.fastapi import create, Jinja2Templates

# _open_lnk_name = "open_app.lnk"
api: sly.Api = sly.Api.from_env()

app = FastAPI()
sly_app = create()

app_root_directory = str(pathlib.Path(__file__).parent.absolute().parents[0])
sly.logger.info(f"Root source directory: {app_root_directory}")

app.mount("/sly", sly_app)
app.mount("/static", StaticFiles(directory=os.path.join(app_root_directory, 'static')), name="static")

templates_env = Jinja2Templates(directory=os.path.join(app_root_directory, 'templates'))

DataJson()['current_step'] = 1


owner_id = int(os.environ['context.userId'])
team_id = int(os.environ['context.teamId'])
project_id = int(os.environ['modal.state.slyProjectId'])
workspace_id = int(os.environ['context.workspaceId'])

project_info = api.project.get_info_by_id(project_id)
project_meta: sly.ProjectMeta = sly.ProjectMeta.from_json(api.project.get_meta(project_id))

model_info = None
model_meta: sly.ProjectMeta = None

DataJson()["ownerId"] = owner_id
DataJson()["teamId"] = team_id

StateJson()["activeStep"] = 1
StateJson()["restartFrom"] = None
