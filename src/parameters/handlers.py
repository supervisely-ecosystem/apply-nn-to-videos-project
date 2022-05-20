from fastapi import Depends

import supervisely
from supervisely import logger



@g.my_app.callback("apply_parameters")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def apply_parameters(api: sly.Api, task_id, context, state, app_logger):
    g.finish_step(5)


@g.my_app.callback("generate_annotation_example")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def generate_annotation_example(api: sly.Api, task_id, context, state, app_logger):
    try:
        fields = [
            {"field": "data.videoUrl", "payload": None}
        ]
        api.task.set_fields(task_id, fields)

        video_id, frames_range = get_video_for_preview()
        result = g.api.task.send_request(state['sessionId'], "inference_video_id",
                                         data={'videoId': video_id,
                                               'framesRange': frames_range,
                                               'confThres': state['confThres'],
                                               'isPreview': True})

        fields = [
            {"field": "data.videoUrl", "payload": result['preview_url']},
            {"field": "state.previewLoading", "payload": False},
        ]
        api.task.set_fields(task_id, fields)
    except Exception as ex:
        fields = [
            {"field": "state.previewLoading", "payload": False},
        ]
        api.task.set_fields(task_id, fields)
        raise ex
