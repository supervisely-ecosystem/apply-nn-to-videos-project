### some card functional
import supervisely as sly

from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import src.sly_globals as g


def restart(data, state):
    data['done2'] = False


def get_model_info(session_id, state):
    g.model_info = g.api.task.send_request(session_id, "get_session_info", data={}, timeout=3)
    meta_json = g.api.task.send_request(session_id, "get_output_classes_and_tags", data={}, timeout=3)
    g.model_meta = sly.ProjectMeta.from_json(meta_json)

    try:
        state['modelSettings'] = g.api.task.send_request(session_id, "get_custom_inference_settings", data={}).get('settings', None)
        if state['modelSettings'] is None or len(state['modelSettings']) == 0:
            state['modelSettings'] = ''
            sly.logger.info("Model doesn't support custom inference settings.")
    except Exception as ex:
        state['modelSettings'] = ''
        sly.logger.info("Model doesn't support custom inference settings.\n"
                        f"Reason: {repr(ex)}")







def show_model_info():
    DataJson()['connected'] = True
    DataJson()['modelInfo'] = g.model_info

    run_sync(DataJson().synchronize_changes())


def validate_model_type():
    if g.model_info.get('type', '') not in g.supported_model_types:
        raise TypeError(f"Model type isn't in supported types list: {g.supported_model_types}")

    if g.model_info['type'] in g.model_types_without_tracking:
        if g.model_info.get('videos_support', False) is True:
            DataJson()['model_without_tracking'] = True

        else:
            raise TypeError(f"Model doesn't support videos processing")
