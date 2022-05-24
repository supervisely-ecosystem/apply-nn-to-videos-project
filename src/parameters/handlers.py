from fastapi import Depends

import supervisely as sly
from supervisely import logger

import src.sly_globals as g


@g.app.post("apply_parameters")
@sly.timeit
def apply_parameters(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    g.finish_step(5)


@g.app.post("generate_annotation_example")
@sly.timeit
def generate_annotation_example(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
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
