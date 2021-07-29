import sly_globals as g

import supervisely_lib as sly

import choose_classes


def init(data, state):
    state["connectionLoading"] = False

    data["modelInfo"] = {}
    data["connected"] = False
    data["connectionError"] = ""

    data["ssOptions"] = {
        "sessionTags": ["deployed_nn"],
        "showLabel": False,
        "size": "small"
    }

    data["done2"] = False

    state["collapsed2"] = True
    state["disabled2"] = True


def restart(data, state):
    data['done2'] = False


def get_model_info(session_id):
    try:
        meta_json = g.api.task.send_request(session_id, "get_model_meta", data={}, timeout=3)
        g.model_info = g.api.task.send_request(session_id, "get_session_info", data={}, timeout=3)
        g.model_meta = sly.ProjectMeta.from_json(meta_json)
    except Exception as ex:
        return -1
    return 0


def show_model_info():
    fields = [
        {"field": "data.connected", "payload": True},
        {"field": "data.modelInfo", "payload": g.model_info},
    ]

    g.api.app.set_fields(g.task_id, fields)


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


