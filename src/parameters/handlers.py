import yaml
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

        try:
            inf_setting = yaml.safe_load(state["settings"])
        except Exception as e:
            inf_setting = {}
            sly.logger.warn(f'Model Inference launched without additional settings. \n'
                            f'Reason: {e}', exc_info=True)

        video_id, frames_range = card_functions.get_video_for_preview(state)

        annotation_predictions = g.api.task.send_request(state['sessionId'], "inference_video_id",
                                                         data={
                                                             'videoId': video_id,
                                                             'startFrameIndex': frames_range[0],
                                                             'framesCount': frames_range[1] - frames_range[0] + 1,
                                                             'settings': inf_setting
                                                         }, timeout=60 * 60 * 24)['ann']

        frame_to_annotation = card_functions.frame_index_to_annotation(annotation_predictions, frames_range)

        frame_to_annotation = f.filter_annotation_by_classes(frame_to_annotation, g.selected_classes)

        # if state['applyTrackingAlgorithm'] is True:
        #     annotation: sly.VideoAnnotation = card_functions.apply_tracking_algorithm_to_predictions(
        #         frame_to_annotation)
        # else:
        #     annotation: sly.VideoAnnotation = f.get_annotation_from_predictions(frame_to_annotation)

        preview_url = card_functions.get_preview_video(video_id, frame_to_annotation, frames_range)


        DataJson()['videoUrl'] = preview_url

    except Exception as ex:
        logger.warn(f'Cannot generate preview: {repr(ex)}', exc_info=True)
        raise HTTPException(status_code=500, detail={'title': "Cannot generate preview",
                                                     'message': f'{ex}'})
    finally:
        DataJson()['previewLoading'] = False
        run_sync(DataJson().synchronize_changes())
