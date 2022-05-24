from fastapi import Depends

import supervisely as sly
from supervisely import logger

import src.choose_classes.functions as card_functions

import src.sly_functions as f
import src.sly_globals as g


@g.app.post("connect")
@sly.timeit
def connect(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    rc = get_model_info(state['sessionId'])
    if rc == 0:
        classes_rows = card_functions.generate_rows()
        card_functions.fill_table(classes_rows)
        show_model_info()
        f.finish_step(2)
    else:
        fields = [
            {"field": "state.connectionLoading", "payload": False},
        ]
        g.api.app.set_fields(g.task_id, fields)
        raise ConnectionError(f'cannot establish connection with model {state["sessionId"]}')
