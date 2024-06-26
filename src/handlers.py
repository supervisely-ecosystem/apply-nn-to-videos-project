from fastapi import Depends, HTTPException, BackgroundTasks
import traceback

import supervisely as sly
from supervisely.app import DataJson, StateJson
from supervisely.app.widgets import ElementButton
from supervisely.app.fastapi import run_sync
from supervisely import logger

import src.sly_globals as g
import src.sly_functions as f
from src.main import server
import src.functions as functions

from src.ui.choose_classes.choose_classes import choose_classes_widget
from src.ui.parameters.parameters import parameters_widget


### INPUT DATA ###


@server.post("/select_projects_handler/")
@sly.timeit
def select_projects_handler(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    table_rows = functions.choose_videos_generate_rows(g.project_id, state)  # temp solution
    functions.choose_videos_fill_table(table_rows=table_rows, state=state)  # temp solution

    f.finish_step(step_num=1, state=state)


### CONNECT TO MODEL ###


@server.post("/connect-to-model/")
@sly.timeit
def connect(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    DataJson()["model_without_tracking"] = False

    try:
        functions.get_model_info(state["sessionId"], state)
        functions.validate_model_type()
        state["canApplyTrackingAlgorithm"] = bool(
            g.model_info.get("tracking_on_videos_support", True)
        )
        state["applyTrackingAlgorithm"] = state["canApplyTrackingAlgorithm"]

        classes_rows = functions.choose_classes_generate_rows()
        functions.choose_classes_fill_table(classes_rows)
        state["selectedClasses"] = [False for _ in g.available_classes_names]
        g.selected_classes_list = []

        functions.show_model_info()

        f.finish_step(2, state)
    except Exception as ex:
        logger.warn(f"Cannot select preferences: {repr(ex)}", exc_info=True)
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail={"title": "Cannot select preferences", "message": f"{ex}"}
        )

    finally:
        state["connectionLoading"] = False
        run_sync(state.synchronize_changes())
        run_sync(DataJson().synchronize_changes())


@server.post("/restart/2/")
def restart2(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    DataJson()["connected"] = False
    f.finish_step(1, state)


### CHOOSE CLASSES ###


@server.post("/choose_classes/")
@sly.timeit
def choose_classes(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        selected_count = len(g.selected_classes_list)
        if selected_count == 0:
            raise ValueError("No classes selected. Please select one class at least.")

        DataJson()["videoUrl"] = None
        f.finish_step(step_num=3, state=state, next_step=5)
    except Exception as ex:
        logger.warn(f"Cannot select preferences: {repr(ex)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"title": "Cannot select classes", "message": f"{ex}"}
        )


@server.post("/classes_selection_change/")
def selected_classes_changed(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    functions.selected_classes_event(state)


@choose_classes_widget.select_all_classes_button.add_route(
    app=server, route=ElementButton.Routes.BUTTON_CLICKED
)
def select_all_classes_button_clicked(
    state: sly.app.StateJson = Depends(sly.app.StateJson.from_request),
):
    state["selectedClasses"] = [True] * len(g.available_classes_names)
    run_sync(state.synchronize_changes())
    functions.selected_classes_event(state)


@choose_classes_widget.deselect_all_classes_button.add_route(
    app=server, route=ElementButton.Routes.BUTTON_CLICKED
)
def deselect_all_classes_button_clicked(
    state: sly.app.StateJson = Depends(sly.app.StateJson.from_request),
):
    state["selectedClasses"] = [False] * len(g.available_classes_names)
    run_sync(state.synchronize_changes())
    functions.selected_classes_event(state)


@server.post("/restart/3/")
def restart3(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    f.finish_step(2, state)


### CHOOSE VIDEOS ###

#
# @server.post("/load_videos_info/")
# @sly.timeit
# def load_videos_info(api: sly.api, task_id, context, state, app_logger):
#     rows = generate_rows([g.project_id])
#     fill_table(rows)
#
#
# @server.callback("choose_videos")
# @sly.timeit
# def choose_videos(api: sly.api, task_id, context, state, app_logger):
#     selected_count = len(state['selectedVideos'])
#
#     if selected_count == 0:
#         raise ValueError('No videos selected. Please select videos.')
#
#     g.finish_step(4)


### PARAMETERS ###


@server.post("/apply-parameters/")
@sly.timeit
def apply_parameters(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    DataJson()["dstProjectName"] = None
    f.finish_step(5, state)


@server.post("/generate-annotation-example/")
@sly.timeit
def generate_annotation_example(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    try:
        DataJson()["videoUrl"] = None
        DataJson()["previewLoading"] = True
        run_sync(DataJson().synchronize_changes())
        g.inference_cancelled = False

        video_id, frames_range = functions.get_video_for_preview(state)

        model_predictions = f.get_model_inference(
            state,
            video_id=video_id,
            frames_range=frames_range,
            progress_widget=parameters_widget.preview_progress,
        )

        frame_to_annotation = f.frame_index_to_annotation(model_predictions, frames_range)

        frame_to_annotation = f.filter_annotation_by_classes(
            frame_to_annotation, g.selected_classes_list
        )
        preview_url = functions.get_preview_video(video_id, frame_to_annotation, frames_range)

        DataJson()["videoUrl"] = preview_url

    except Exception as ex:
        logger.warn(f"Cannot generate preview: {repr(ex)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"title": "Cannot generate preview", "message": f"{ex}"}
        )
    finally:
        DataJson()["previewLoading"] = False
        run_sync(DataJson().synchronize_changes())


@server.post("/restart/5/")
def restart5(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    f.finish_step(3, state, 5)


### OUTPUT DATA ###


@server.post("/start-annotation/")
@sly.timeit
def start_annotation(
    background_tasks: BackgroundTasks,
    state: sly.app.StateJson = Depends(sly.app.StateJson.from_request),
):
    try:
        DataJson()["annotatingStarted"] = True
        run_sync(DataJson().synchronize_changes())
        StateJson()["canStop"] = False
        StateJson().send_changes()
        g.inference_cancelled = False
        g.inference_session = None
        g.inference_request_uuid = None

        background_tasks.add_task(functions.annotate_videos, state=state)
    except Exception as ex:
        DataJson()["annotatingStarted"] = False
        logger.warn(f"Cannot apply NN to Videos Project: {repr(ex)}", exc_info=True)
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={"title": "Cannot apply NN to Videos Project", "message": f"{ex}"},
        )

    finally:
        run_sync(DataJson().synchronize_changes())


@server.post("/restart/6")
def restart6(state: sly.app.StateJson = Depends(sly.app.StateJson.from_request)):
    f.finish_step(5, state)


@server.post("/stop-annotation/")
def stop_annotation(
    background_tasks: BackgroundTasks,
    state: sly.app.StateJson = Depends(sly.app.StateJson.from_request),
):
    StateJson()["canStop"] = False
    StateJson().send_changes()
    background_tasks.add_task(functions.stop_annotate_videos, state=state)
