### some card functional
import supervisely as sly

from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import src.sly_globals as g


def restart(data, state):
    data['done2'] = False


def get_model_info(session_id):
    meta_json = g.api.task.send_request(session_id, "get_model_meta", data={}, timeout=3)
    g.model_info = g.api.task.send_request(session_id, "get_session_info", data={}, timeout=3)
    g.model_meta = sly.ProjectMeta.from_json(meta_json)


def show_model_info():
    DataJson()['connected'] = True
    DataJson()['modelInfo'] = g.model_info

    run_sync(DataJson().synchronize_changes())
