from fastapi import Depends, HTTPException

import supervisely as sly
from supervisely import logger


import src.sly_globals as g
import src.sly_functions as f
from supervisely.app import DataJson


@g.app.post("/choose_classes/")
@sly.timeit
def choose_classes(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        selected_count = len(state['selectedClasses'])
        if selected_count == 0:
            raise ValueError('No classes selected. Please select one class at least .')
        g.selected_classes = state['selectedClasses']
        f.finish_step(step_num=3, state=state, next_step=5)
    except Exception as ex:
        logger.warn(f'Cannot select preferences: {repr(ex)}', exc_info=True)
        raise HTTPException(status_code=500, detail={'title': "Cannot select classes",
                                                     'message': f'{ex}'})




