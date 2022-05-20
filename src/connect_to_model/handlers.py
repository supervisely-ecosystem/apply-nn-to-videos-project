from fastapi import Depends

import supervisely
from supervisely import logger



@g.my_app.callback("connect")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def connect(api: sly.Api, task_id, context, state, app_logger):
    rc = get_model_info(state['sessionId'])
    if rc == 0:
        classes_rows = choose_classes.generate_rows()
        choose_classes.fill_table(classes_rows)
        show_model_info()
        g.finish_step(2)
    else:
        fields = [
            {"field": "state.connectionLoading", "payload": False},
        ]
        g.api.app.set_fields(g.task_id, fields)
        raise ConnectionError(f'cannot establish connection with model {state["sessionId"]}')
