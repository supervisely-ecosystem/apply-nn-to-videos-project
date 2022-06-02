from fastapi import Depends, HTTPException

import supervisely as sly
from supervisely import logger

import src.connect_to_model.functions as card_functions
import src.choose_classes.functions as choose_classes_functions


import src.sly_functions as f
import src.sly_globals as g
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync


@g.app.post("/connect-to-model/")
@sly.timeit
def connect(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        card_functions.get_model_info(state['sessionId'])
        classes_rows = choose_classes_functions.generate_rows()
        choose_classes_functions.fill_table(classes_rows)
        card_functions.show_model_info()
        f.finish_step(2, state)
    except Exception as ex:
        logger.warn(f'Cannot select preferences: {repr(ex)}', exc_info=True)
        raise HTTPException(status_code=500, detail={'title': "Cannot select preferences",
                                                     'message': f'{ex}'})

    finally:
        state['connectionLoading'] = False
        run_sync(DataJson().synchronize_changes())

