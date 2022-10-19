import yaml
from fastapi import Depends, HTTPException

import supervisely as sly
from supervisely import logger

from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import src.sly_globals as g
import src.sly_functions as f

import src.parameters.functions as card_functions
import src.parameters.widgets as card_widgets


@g.app.post("/apply-parameters/")
@sly.timeit
def apply_parameters(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    DataJson()['dstProjectName'] = None
    f.finish_step(5, state)


@g.app.post("/generate-annotation-example/")
@sly.timeit
def generate_annotation_example(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        DataJson()['videoUrl'] = None
        DataJson()['previewLoading'] = True
        run_sync(DataJson().synchronize_changes())

        video_id, frames_range = card_functions.get_video_for_preview(state)

        with card_widgets.preview_progress(message='Gathering Predictions from Model', total=1) as progress:
            model_predictions = f.get_model_inference(state, video_id=video_id, frames_range=frames_range)
            progress.update()

        frame_to_annotation = f.frame_index_to_annotation(model_predictions, frames_range)

        frame_to_annotation = f.filter_annotation_by_classes(frame_to_annotation, g.selected_classes_list)
        preview_url = card_functions.get_preview_video(video_id, frame_to_annotation, frames_range)

        DataJson()['videoUrl'] = preview_url

    except Exception as ex:
        logger.warn(f'Cannot generate preview: {repr(ex)}', exc_info=True)
        raise HTTPException(status_code=500, detail={'title': "Cannot generate preview",
                                                     'message': f'{ex}'})
    finally:
        DataJson()['previewLoading'] = False
        run_sync(DataJson().synchronize_changes())


@g.app.post('/restart/5/')
def restart(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    f.finish_step(3, state, 5)

