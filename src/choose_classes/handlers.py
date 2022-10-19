from fastapi import Depends, HTTPException
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import supervisely as sly
from supervisely import logger


import src.sly_globals as g
import src.sly_functions as f


import src.choose_classes.functions as card_functions
import src.choose_classes.widgets as card_widgets
from supervisely.app.widgets import ElementButton


@g.app.post("/choose_classes/")
@sly.timeit
def choose_classes(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        selected_count = len(g.selected_classes_list)
        if selected_count == 0:
            raise ValueError('No classes selected. Please select one class at least.')

        DataJson()['videoUrl'] = None
        f.finish_step(step_num=3, state=state, next_step=5)
    except Exception as ex:
        logger.warn(f'Cannot select preferences: {repr(ex)}', exc_info=True)
        raise HTTPException(status_code=500, detail={'title': "Cannot select classes",
                                                     'message': f'{ex}'})


@g.app.post('/classes_selection_change/')
def selected_classes_changed(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    card_functions.selected_classes_event(state)


@card_widgets.select_all_classes_button.add_route(app=g.app, route=ElementButton.Routes.BUTTON_CLICKED)
def select_all_classes_button_clicked(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    state["selectedClasses"] = [True] * len(g.available_classes_names)
    run_sync(state.synchronize_changes())
    card_functions.selected_classes_event(state)


@card_widgets.deselect_all_classes_button.add_route(app=g.app, route=ElementButton.Routes.BUTTON_CLICKED)
def deselect_all_classes_button_clicked(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    state["selectedClasses"] = [False] * len(g.available_classes_names)
    run_sync(state.synchronize_changes())
    card_functions.selected_classes_event(state)


@g.app.post('/restart/3/')
def restart(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    f.finish_step(2, state)


