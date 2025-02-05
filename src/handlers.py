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


@server.post("/test/select_projects_handler")
@sly.timeit
def select_projects_handler():
    state = StateJson()
    table_rows = functions.choose_videos_generate_rows(g.project_id, state)  # temp solution
    functions.choose_videos_fill_table(table_rows=table_rows, state=state)  # temp solution

    f.finish_step(step_num=1, state=state)


### CONNECT TO MODEL ###


@server.post("/connect-to-model/")
@sly.timeit
def connect():
    DataJson()["model_without_tracking"] = False
    state = StateJson()
    try:
        functions.get_model_info(state["sessionId"], state)
        functions.validate_model_type()

        tracking_algorithm = state["selectedTrackingAlgorithm"]
        functions.get_default_tracking_settings(tracking_algorithm)

        state["modelSettings"] = g.model_settings + "\n" + g.tracking_settings
        state["canApplyTrackingAlgorithm"] = bool(
            g.model_info.get("tracking_on_videos_support", True)
        )
        if g.model_info.get("task type") == "promptable segmentation":
            state["canApplyTrackingAlgorithm"] = False
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
def restart2():
    DataJson()["connected"] = False
    state = StateJson()
    f.finish_step(1, state)


### CHOOSE CLASSES ###


@server.post("/choose_classes/")
@sly.timeit
def choose_classes():
    try:
        selected_count = len(g.selected_classes_list)
        if selected_count == 0:
            raise ValueError("No classes selected. Please select one class at least.")

        DataJson()["videoUrl"] = None
        state = StateJson()
        f.finish_step(step_num=3, state=state, next_step=5)
    except Exception as ex:
        logger.warn(f"Cannot select preferences: {repr(ex)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"title": "Cannot select classes", "message": f"{ex}"}
        )


@server.post("/classes_selection_change/")
def selected_classes_changed():
    state = StateJson()
    functions.selected_classes_event(state)


@choose_classes_widget.select_all_classes_button.add_route(
    app=server, route=ElementButton.Routes.BUTTON_CLICKED
)
def select_all_classes_button_clicked():
    state = StateJson()
    state["selectedClasses"] = [True] * len(g.available_classes_names)
    run_sync(state.synchronize_changes())
    functions.selected_classes_event(state)


@choose_classes_widget.deselect_all_classes_button.add_route(
    app=server, route=ElementButton.Routes.BUTTON_CLICKED
)
def deselect_all_classes_button_clicked():
    state = StateJson()
    state["selectedClasses"] = [False] * len(g.available_classes_names)
    run_sync(state.synchronize_changes())
    functions.selected_classes_event(state)


@server.post("/restart/3/")
def restart3():
    state = StateJson()
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
def apply_parameters():
    state = StateJson()
    DataJson()["dstProjectName"] = None
    f.finish_step(5, state)


@server.post("/tracking-algorithm-changed/")
@sly.timeit
def algorithm_changed():
    state = StateJson()
    tracker_algorithm = state["selectedTrackingAlgorithm"]
    functions.get_default_tracking_settings(tracker_algorithm)
    state["modelSettings"] = g.model_settings + "\n" + g.tracking_settings
    run_sync(state.synchronize_changes())


@server.post("/generate-annotation-example/")
@sly.timeit
def generate_annotation_example():
    try:
        state = StateJson()
        DataJson()["videoUrl"] = None
        DataJson()["previewLoading"] = True
        run_sync(DataJson().synchronize_changes())
        g.inference_cancelled = False

        video_id, frame_index = functions.get_random_frame(state)

        model_predictions = f.get_model_inference(
            state,
            video_id=video_id,
            frames_range=(frame_index, frame_index),
            progress_widget=parameters_widget.preview_progress,
        )

        frame_to_annotation = f.frame_index_to_annotation(
            model_predictions, (frame_index, frame_index)
        )
        frame_to_annotation = f.filter_annotation_by_classes(
            frame_to_annotation, g.selected_classes_list
        )

        preview_url = functions.get_preview_image(video_id, frame_to_annotation, frame_index)
        DataJson()["frameUrl"] = preview_url

        # video_id, frames_range = functions.get_video_for_preview(state)

        # model_predictions = f.get_model_inference(
        #     state,
        #     video_id=video_id,
        #     frames_range=frames_range,
        #     progress_widget=parameters_widget.preview_progress,
        # )

        # frame_to_annotation = f.frame_index_to_annotation(model_predictions, frames_range)

        # frame_to_annotation = f.filter_annotation_by_classes(
        #     frame_to_annotation, g.selected_classes_list
        # )
        # preview_url = functions.get_preview_video(video_id, frame_to_annotation, frames_range)

        # DataJson()["videoUrl"] = preview_url

    except Exception as ex:
        logger.warn(f"Cannot generate preview: {repr(ex)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"title": "Cannot generate preview", "message": f"{ex}"}
        )
    finally:
        DataJson()["previewLoading"] = False
        run_sync(DataJson().synchronize_changes())


@server.post("/restart/5/")
def restart5():
    state = StateJson()
    f.finish_step(3, state, 5)


### OUTPUT DATA ###


@server.post("/start-annotation/")
@sly.timeit
def start_annotation(background_tasks: BackgroundTasks):
    try:
        state = StateJson()
        DataJson()["annotatingStarted"] = True
        run_sync(DataJson().synchronize_changes())
        StateJson()["canStop"] = False
        StateJson().send_changes()
        g.inference_cancelled = False
        g.inference_session = None
        g.inference_request_uuid = None

        functions.annotate_videos(state=state)
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
def restart6():
    state = StateJson()
    f.finish_step(5, state)


@server.post("/stop-annotation/")
def stop_annotation(background_tasks: BackgroundTasks):
    StateJson()["canStop"] = False
    StateJson().send_changes()
    state = StateJson()
    background_tasks.add_task(functions.stop_annotate_videos, state=state)
