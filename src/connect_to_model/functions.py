### some card functional
from typing import Any, Dict, List, Optional
import supervisely as sly

from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import src.sly_globals as g
import yaml


def restart(data, state):
    data['done2'] = False


def get_model_info(session_id, state):
    g.model_info = g.api.task.send_request(session_id, "get_session_info", data={}, timeout=3)
    sly.logger.info('Model info', extra=g.model_info)

    meta_json = g.api.task.send_request(session_id, "get_output_classes_and_tags", data={}, timeout=3)
    sly.logger.info(f'Model meta: {meta_json}')
    g.model_meta = sly.ProjectMeta.from_json(meta_json)

    try:
        state['modelSettings'] = g.api.task.send_request(session_id, "get_custom_inference_settings", data={}).get('settings', None)
        if state['modelSettings'] is None or len(state['modelSettings']) == 0:
            raise ValueError()
        elif isinstance(state["modelSettings"], dict):
            state["modelSettings"] = yaml.dump(state["modelSettings"], allow_unicode=True)
        sly.logger.info(f'Custom inference settings: {state["modelSettings"]}')
    except Exception as ex:
        state['modelSettings'] = ''
        sly.logger.info("Model doesn't support custom inference settings.\n"
                        f"Reason: {repr(ex)}")


def show_model_info():
    DataJson()['connected'] = True
    DataJson()['modelInfo'] = format_info(g.model_info, ["async_image_inference_support"])

    run_sync(DataJson().synchronize_changes())


def format_info(model_info: Dict[str, Any], exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    formated_info = {}
    exclude = [] if exclude is None else exclude

    for name, data in model_info.items():
        if name in exclude:
            sly.logger.debug(f"Field {name} excluded from session info")
            continue
    
        new_name = name.replace("_", " ").capitalize()
        formated_info[new_name] = data

    return formated_info


def validate_model_type():
    # DataJson()['model_without_tracking'] = True
    # if g.model_info.get('type', '') not in g.supported_model_types:
    #     raise TypeError(f"Model type isn't in supported types list: {g.supported_model_types}")
    #
    # if g.model_info['type'] in g.model_types_without_tracking:
    if g.model_info.get('videos_support', True) is True:
        DataJson()['model_without_tracking'] = True

    else:
        raise TypeError(f"Model doesn't support videos processing")
