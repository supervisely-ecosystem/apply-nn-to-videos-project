from fastapi import Depends, HTTPException
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import supervisely as sly
from supervisely import logger

import src.sly_globals as g

import src.output_data.functions as card_functions


@g.app.post("/start-annotation/")
@sly.timeit
def start_annotation(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        DataJson()['annotatingStarted'] = True
        run_sync(DataJson().synchronize_changes())

        card_functions.annotate_videos(state)

        DataJson()['done6'] = True
    except Exception as ex:
        logger.warn(f'Cannot apply NN to Videos Project: {repr(ex)}', exc_info=True)
        raise HTTPException(status_code=500, detail={'title': "Cannot apply NN to Videos Project",
                                                     'message': f'{ex}'})

    finally:
        DataJson()['annotatingStarted'] = False
        run_sync(DataJson().synchronize_changes())

