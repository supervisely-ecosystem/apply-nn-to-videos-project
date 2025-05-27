import os
import pathlib
from typing import Dict, List

import torch.cuda

import supervisely as sly

from supervisely.app import DataJson, StateJson
from supervisely.api.video.video_api import VideoInfo


app_root_directory = str(pathlib.Path(__file__).parent.absolute().parents[0])
sly.logger.info(f"Root source directory: {app_root_directory}")

temp_dir = os.path.join(app_root_directory, "temp")
preview_frames_path = os.path.join(temp_dir, "preview_frames")

# for debug
from dotenv import load_dotenv

if sly.is_development():
    load_dotenv(os.path.join(app_root_directory, "local.env"))
    load_dotenv(os.path.expanduser("~/supervisely.env"))


class AnnotatorModes:
    DIRECT = "direct"
    DEEPSORT = "deepsort"


api: sly.Api = sly.Api.from_env()

supported_model_types = [
    "Semantic Segmentation",
    "Object Detection",
    "Instance Segmentation",
    "Tracking",
]
model_types_without_tracking = [
    "Semantic Segmentation",
    "Object Detection",
    "Instance Segmentation",
]

DataJson()["current_step"] = 1
DataJson()["mode"] = AnnotatorModes.DIRECT


owner_id = int(os.environ["context.userId"])
team_id = int(os.environ["context.teamId"])
project_id = int(os.environ["modal.state.slyProjectId"])
workspace_id = int(os.environ["context.workspaceId"])

project_info = api.project.get_info_by_id(project_id)
project_meta: sly.ProjectMeta = sly.ProjectMeta.from_json(api.project.get_meta(project_id))

datasets = api.dataset.get_list(project_id, recursive=True)
ds_video_map: Dict[int, List[VideoInfo]] = None
model_info = None
model_meta: sly.ProjectMeta = None
device = (
    torch.device("cuda:0")
    if torch.cuda.is_available() and torch.cuda.device_count() > 0
    else torch.device("cpu")
)

DataJson()["ownerId"] = owner_id
DataJson()["teamId"] = team_id
DataJson()["instanceAddress"] = os.getenv("SERVER_ADDRESS")

StateJson()["activeStep"] = 1
StateJson()["restartFrom"] = None

selected_classes_list = []
available_classes_names = []

inference_request_uuid = None
inference_session = None
inference_cancelled = False

deepsort_clip_encoder = None

model_settings = ""
tracking_settings = ""

result_meta = None

dst_datasets = {} # src dataset id -> dst dataset info
