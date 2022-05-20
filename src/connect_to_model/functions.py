### some card functional

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

