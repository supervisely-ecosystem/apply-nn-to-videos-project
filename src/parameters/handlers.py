from fastapi import Depends, HTTPException

import supervisely as sly
from supervisely import logger

from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import src.sly_globals as g
import src.sly_functions as f

import src.parameters.functions as card_functions


@g.app.post("/apply-parameters/")
@sly.timeit
def apply_parameters(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    f.finish_step(5, state)


@g.app.post("/generate-annotation-example/")
@sly.timeit
def generate_annotation_example(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        DataJson()['videoUrl'] = None
        DataJson()['previewLoading'] = True
        run_sync(DataJson().synchronize_changes())

        video_id, frames_range = card_functions.get_video_for_preview(state)
        result = g.api.task.send_request(state['sessionId'], "inference_video_id",
                                         data={'videoId': video_id,
                                               'framesRange': frames_range,
                                               'confThres': state['confThres'],
                                               'isPreview': True})

        DataJson()['videoUrl'] = result['preview_url']

    except Exception as ex:
        logger.warn(f'Cannot generate preview: {repr(ex)}', exc_info=True)
        raise HTTPException(status_code=500, detail={'title': "Cannot generate preview",
                                                      'message': f'{ex}'})
    finally:
        DataJson()['previewLoading'] = False
        run_sync(DataJson().synchronize_changes())
