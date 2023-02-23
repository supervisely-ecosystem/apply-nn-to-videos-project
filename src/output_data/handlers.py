import traceback

from fastapi import Depends, HTTPException, BackgroundTasks
from supervisely.app import DataJson, StateJson
from supervisely.app.fastapi import run_sync

import supervisely as sly
from supervisely import logger

import src.sly_functions as f
import src.sly_globals as g

import src.output_data.functions as card_functions


@g.app.post("/start-annotation/")
@sly.timeit
def start_annotation(background_tasks: BackgroundTasks,
                     state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        DataJson()['annotatingStarted'] = True
        run_sync(DataJson().synchronize_changes())
        StateJson()["canStop"] = False
        StateJson().send_changes()

        background_tasks.add_task(card_functions.annotate_videos, state=state)
    except Exception as ex:
        DataJson()['annotatingStarted'] = False
        logger.warn(f'Cannot apply NN to Videos Project: {repr(ex)}', exc_info=True)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail={'title': "Cannot apply NN to Videos Project",
                                                     'message': f'{ex}'})

    finally:
        run_sync(DataJson().synchronize_changes())


@g.app.post('/restart/6')
def restart(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    f.finish_step(5, state)


@g.app.post("/stop-annotation/")
def stop_annotation(background_tasks: BackgroundTasks,
                     state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        background_tasks.add_task(card_functions.stop_annotate_videos, state=state)
    except Exception as ex:
        DataJson()['annotatingStarted'] = True
        logger.warn(f'Cannot stop: {repr(ex)}', exc_info=True)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail={'title': "Cannot stop",
                                                     'message': f'{ex}'})

    finally:
        run_sync(DataJson().synchronize_changes())
