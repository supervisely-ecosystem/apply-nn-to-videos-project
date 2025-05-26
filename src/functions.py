import os
import shutil
from typing import Any, Dict, List, Optional
import yaml

import supervisely as sly
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import src.sly_globals as g
from src.ui.parameters.parameters import parameters_widget
from src.ui.output_data.output_data import output_data_widget
import src.workflow as w
from src.boxmot_tracking import apply_boxmot


### CONNECT TO MODEL ###


def restart2(data, state):
    data["done2"] = False


def get_model_info(session_id, state):
    g.model_info = g.api.task.send_request(session_id, "get_session_info", data={}, timeout=3)
    sly.logger.info("Model info", extra=g.model_info)

    meta_json = g.api.task.send_request(
        session_id, "get_output_classes_and_tags", data={}, timeout=3
    )
    sly.logger.info(f"Model meta: {meta_json}")
    g.model_meta = sly.ProjectMeta.from_json(meta_json)

    try:
        g.model_settings = g.api.task.send_request(
            session_id, "get_custom_inference_settings", data={}
        ).get("settings", None)
        if g.model_settings is None or len(g.model_settings) == 0:
            raise ValueError("Failed to get model settings")
        elif isinstance(g.model_settings, dict):
            g.model_settings = yaml.dump(g.model_settings, allow_unicode=True)
        sly.logger.info(f"Custom inference settings: {g.model_settings}")
        g.model_settings = "# Model settings:\n" + g.model_settings

    except Exception as ex:
        g.model_settings = ""
        sly.logger.info("Model doesn't support custom inference settings.\n" f"Reason: {repr(ex)}")


def get_model_and_tracking_settings(state):
    settings = state["modelSettings"]
    if "#Tracking settings:" in settings:
        g.model_settings, g.tracking_settings = settings.split("#Tracking settings:")
        return yaml.safe_load(g.model_settings), yaml.safe_load(g.tracking_settings)
    else:
        g.model_settings = settings
        g.tracking_settings = ""
        return yaml.safe_load(g.model_settings), None


def get_default_tracking_settings(tracker_type: str = "boxmot"):
    try:
        if tracker_type == "boxmot":
            settings = {
                "track_high_thresh": 0.6,
                "track_low_thresh": 0.1,
                "new_track_thresh": 0.7,
                "match_thresh": 0.8,
            }
            g.tracking_settings = "#Tracking settings:\n" + yaml.dump(settings, allow_unicode=True)
        else:
            g.tracking_settings = ""
    except Exception as ex:
        g.tracking_settings = ""
        sly.logger.info(
            f"Failed to get tracking settings for {tracker_type}.\n" f"Reason: {repr(ex)}"
        )


def show_model_info():
    DataJson()["connected"] = True
    DataJson()["modelInfo"] = format_info(g.model_info, ["async_image_inference_support"])

    run_sync(DataJson().synchronize_changes())


def format_info(model_info: Dict[str, Any], exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    formated_info = {}
    exclude = [] if exclude is None else exclude

    for name, data in model_info.items():
        if name in exclude:
            sly.logger.debug(f"Field {name} excluded from session info")
            continue

        new_name = name.replace("_", " ").capitalize()
        formated_info[new_name] = data

    return formated_info


def validate_model_type():
    # DataJson()['model_without_tracking'] = True
    # if g.model_info.get('type', '') not in g.supported_model_types:
    #     raise TypeError(f"Model type isn't in supported types list: {g.supported_model_types}")
    #
    # if g.model_info['type'] in g.model_types_without_tracking:
    if g.model_info.get("videos_support", True) is True:
        DataJson()["model_without_tracking"] = True

    else:
        raise TypeError(f"Model doesn't support videos processing")


### CHOOSE CLASSES ###


def restart3(data, state):
    data["done3"] = False


def choose_classes_generate_rows():
    rows = []
    g.available_classes_names = []
    obj_classes = g.model_meta.obj_classes
    for obj_class in obj_classes:
        rows.append(
            {
                "label": f"{obj_class.name}",
                "shapeType": f"{obj_class.geometry_type.geometry_name()}",
                "color": f'{"#%02x%02x%02x" % tuple(obj_class.color)}',
            }
        )

        g.available_classes_names.append(obj_class.name)
    return rows


def choose_classes_fill_table(table_rows):
    DataJson()["classesTable"] = table_rows
    run_sync(DataJson().synchronize_changes())


def selected_classes_event(state):
    g.selected_classes_list = []
    for idx, class_name in enumerate(g.available_classes_names):
        if state["selectedClasses"][idx] is True:
            g.selected_classes_list.append(class_name)


### CHOOSE VIDEOS ###

import src.sly_globals as g
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync


def restart4(data, state):
    data["done4"] = False


def get_videos_info(project_id, state):
    general_videos_info = []
    frames_min = {}
    frames_max = {}

    g.ds_video_map = {}
    for ds in g.datasets:
        videos_info = g.api.video.get_list(ds.id)
        g.ds_video_map[ds.id] = []

        for video_info in videos_info:
            g.ds_video_map[ds.id].append(video_info)
            general_videos_info.append(
                {
                    "name": video_info.name,
                    "dataset": ds.name,
                    "framesCount": video_info.frames_count,
                    "framesRange": "-",
                    "isDisabled": True if video_info.frames_count < 5 else False,
                    "videoId": video_info.id,
                    "videoHash": video_info.hash,
                    "frame_shape": (video_info.frame_height, video_info.frame_width),
                }
            )

            frames_min[video_info.name] = 0
            frames_max[video_info.name] = video_info.frames_count - 1

    state["framesMin"] = frames_min
    state["framesMax"] = frames_max

    return general_videos_info


def choose_videos_generate_rows(project_id, state) -> list:
    return get_videos_info(project_id, state)


def choose_videos_fill_table(table_rows, state):
    selected_videos = [row["name"] for row in table_rows if not row["isDisabled"]]

    state["statsLoaded"] = True
    state["selectedVideos"] = selected_videos

    DataJson()["videosTable"] = table_rows

    run_sync(DataJson().synchronize_changes())
    run_sync(state.synchronize_changes())


### PARAMETERS ###


import supervisely as sly

import random
import src.sly_globals as g
import src.sly_functions as f
from supervisely.app import DataJson


def restart5(data, state):
    data["done5"] = False


def get_video_for_preview(state):
    videos_table = DataJson()["videosTable"]
    selected_videos = state["selectedVideos"]

    frames_min = state["framesMin"]
    frames_max = state["framesMax"]

    random.shuffle(selected_videos)
    video_name = selected_videos[0]

    video_info = [row for row in videos_table if row["name"] == video_name][0]

    start_frame = 0
    if frames_max[video_info["name"]] <= 30:
        end_frame = frames_max[video_info["name"]]
    else:
        end_frame = frames_max[video_info["name"]] + 1
        while end_frame > frames_max[video_info["name"]]:
            start_frame = random.randint(
                frames_min[video_info["name"]], frames_max[video_info["name"]]
            )
            end_frame = start_frame + 29

    return video_info["videoId"], (start_frame, end_frame)


def get_random_frame(state):
    videos_table = DataJson()["videosTable"]
    selected_videos = state["selectedVideos"]

    frames_min = state["framesMin"]
    frames_max = state["framesMax"]

    random.shuffle(selected_videos)
    video_name = selected_videos[0]

    video_info = [row for row in videos_table if row["name"] == video_name][0]
    frame_index = random.randint(frames_min[video_info["name"]], frames_max[video_info["name"]])
    return video_info["videoId"], frame_index


def get_preview_image(video_id, frame_to_annotation, frame_index):
    with parameters_widget.preview_progress(message="Downloading Frame", total=1) as progress:
        frame_to_image_path = f.download_frames_range(
            video_id, g.preview_frames_path, (frame_index, frame_index), pbar_cb=progress.update
        )

    with parameters_widget.preview_progress(message="Generating Preview", total=1) as progress:
        f.draw_labels_on_frames(frame_to_image_path, frame_to_annotation)
        local_image_path = frame_to_image_path[frame_index]
        progress.update(1)

    preview_image_name = f"preview_image{sly.rand_str(8)}.jpg"
    preview_image_path = os.path.join(g.app_root_directory, "static", preview_image_name)
    shutil.copy(local_image_path, preview_image_path)
    url = f"static/{preview_image_name}"
    return url


def get_preview_video(video_id, frame_to_annotation, frames_range):
    with parameters_widget.preview_progress(
        message="Downloading Frames", total=abs(frames_range[0] - frames_range[1]) + 1
    ) as progress:
        frames_to_image_path = f.download_frames_range(
            video_id, g.preview_frames_path, frames_range, pbar_cb=progress.update
        )

    with parameters_widget.preview_progress(message="Generating Preview", total=1) as progress:
        f.draw_labels_on_frames(frames_to_image_path, frame_to_annotation)
        local_video_path = f.generate_video_from_frames(g.preview_frames_path)
        progress.update(1)

    # with parameters_widget.preview_progress(message='Uploading Video', total=f.get_video_size(local_video_path), unit='B', unit_scale=True) as progress:
    with parameters_widget.preview_progress(message="Uploading Video", total=1) as progress:
        video_info = f.upload_video_to_sly(local_video_path)

    return video_info.storage_path


### OUTPUT DATA ###

import src.sly_functions as f


def restart6(data, state):
    data["done6"] = False


def shutdown_app():
    try:
        sly.app.fastapi.shutdown()
    except KeyboardInterrupt:
        sly.logger.info("Application shutdown successfully")


def init_project_remotely(project_name="ApplyNNtoVideoProject"):
    project = g.api.project.create(
        g.workspace_id,
        project_name,
        type=sly.ProjectType.VIDEOS,
        change_name_if_conflict=True,
    )
    classes_to_keep = [c for c in g.model_meta.obj_classes if c.name in g.selected_classes_list]
    meta = g.model_meta.clone(classes_to_keep)
    g.result_meta = g.api.project.update_meta(project.id, meta)

    return project.id


def upload_to_project(video_data, annotation: sly.VideoAnnotation, dataset_id, progress):
    # video_hash = video_data["videoHash"]
    video_id = video_data["videoId"]
    video_name = video_data["name"]
    sly.logger.debug(f"Video data: {video_data}")
    # file_info = g.api.video.upload_hash(dataset_id, video_name, video_hash)
    file_info = g.api.video.upload_id(dataset_id, video_name, video_id)
    progress_cb = progress(message="Uploading annotation", total=len(annotation.figures))
    g.api.video.annotation.append(file_info.id, annotation, progress_cb=progress_cb)


def get_video_annotation(video_data, state) -> sly.VideoAnnotation:
    frames_min = state["framesMin"]
    frames_max = state["framesMax"]
    frames_range = (frames_min[video_data["name"]], frames_max[video_data["name"]])
    video_id = video_data["videoId"]

    if state["applyTrackingAlgorithm"] is True and state["selectedTrackingAlgorithm"] != "boxmot":
        try:
            ann_json = f.track_on_model(
                state,
                video_id=video_id,
                frames_range=frames_range,
                progress_widget=output_data_widget.current_video_progress,
            )
            return sly.VideoAnnotation.from_json(ann_json, g.model_meta)
        except Exception:
            sly.logger.warning(
                "Failed to apply tracking on model, fallback to default mode", exc_info=True
            )

    model_predictions = f.get_model_inference(
        state,
        video_id=video_id,
        frames_range=frames_range,
        progress_widget=output_data_widget.current_video_progress,
    )

    frame_to_annotation = f.frame_index_to_annotation(model_predictions, frames_range)
    frame_to_annotation = f.filter_annotation_by_classes(
        frame_to_annotation, g.selected_classes_list
    )

    if state["applyTrackingAlgorithm"] is True:
        with output_data_widget.current_video_progress(
            message=f'Applying tracking algorithm ({state["selectedTrackingAlgorithm"]})',
            total=abs(frames_range[0] - frames_range[1]) + 1,
        ) as progress:
            tracking_algorithm = state["selectedTrackingAlgorithm"]
            if tracking_algorithm == "boxmot":
                _, tracking_settings = get_model_and_tracking_settings(state)
                video_ann = apply_boxmot(
                    g.api,
                    video_id=video_id,
                    frame_shape=video_data["frame_shape"],
                    frame_to_annotation=frame_to_annotation,
                    device=state["device"],
                    work_dir=g.temp_dir,
                    model_meta=g.result_meta,
                    progress=progress,
                    tracking_settings=tracking_settings,
                )
            else:
                video_ann = f.apply_tracking_algorithm_to_predictions(
                    state=state,
                    video_id=video_id,
                    frames_range=frames_range,
                    frame_to_annotation=frame_to_annotation,
                    tracking_algorithm=tracking_algorithm,
                    pbar_cb=progress.update,
                )
            return video_ann
    else:
        obj_classes = g.result_meta.obj_classes
        return annotations_to_video_annotation(
            frame_to_annotation, obj_classes, video_data["frame_shape"]
        )
    

def get_dataset(dataset_id: int, datasets: Optional[List[sly.DatasetInfo]] = None) -> sly.DatasetInfo:
    if datasets is None:
        datasets = g.datasets
    ds = next((ds for ds in g.datasets if ds.id == dataset_id), None)
    if ds is None:
        raise ValueError(f"Dataset with id {dataset_id} not found in the project {g.project_id}")
    return ds


def get_or_create_dst_dataset(src_dataset_id: int, dst_project_id: int):
    if src_dataset_id in g.dst_datasets:
        return g.dst_datasets[src_dataset_id]
    src_dataset = get_dataset(src_dataset_id)
    if src_dataset.parent_id is not None:
        get_or_create_dst_dataset(src_dataset.parent_id, dst_project_id)
    parent_dst_dataset_id = None
    parent_dst_dataset = g.dst_datasets.get(src_dataset.parent_id, None)
    if parent_dst_dataset is not None:
        parent_dst_dataset_id = parent_dst_dataset.id
    return g.api.dataset.create(project_id=dst_project_id, name=src_dataset.name, parent_id=parent_dst_dataset_id, change_name_if_conflict=True)


def annotate_videos(state):
    selected_videos_names = state["selectedVideos"]

    w.workflow_input(g.api, project_id=g.project_id, session_id=state["sessionId"])
    output_project_name = state["expId"]
    project_id = init_project_remotely(project_name=output_project_name)

    for ds_id in g.ds_video_map:
        src_dataset = get_dataset(ds_id, g.datasets)
        dst_dataset = get_or_create_dst_dataset(src_dataset.id, project_id)

        videos_table = DataJson()["videosTable"]

        ds_name = src_dataset.name
        ds_video_names = [v.name for v in g.ds_video_map[ds_id]]
        selected_videos_data = [
            row
            for row in videos_table
            if row["name"] in selected_videos_names
            and row["name"] in ds_video_names
            and row["dataset"] == ds_name
        ]

        for video_data in output_data_widget.apply_nn_to_video_project_progress(
            selected_videos_data, message=f"Inference Videos in dataset: {ds_name}"
        ):
            annotation: sly.VideoAnnotation = get_video_annotation(video_data, state)
            upload_to_project(
                video_data, annotation, dst_dataset.id, output_data_widget.current_video_progress
            )

    res_project = g.api.project.get_info_by_id(project_id)
    output_data_widget.set_project_thumbnail(res_project)
    w.workflow_output(g.api, res_project.id)
    DataJson().update(
        {
            "dstProjectName": res_project.name,
        }
    )

    DataJson()["done6"] = True
    DataJson()["annotatingStarted"] = False

    run_sync(DataJson().synchronize_changes())
    shutdown_app()


def stop_annotate_videos(state):
    if g.inference_session or g.inference_request_uuid:
        sly.logger.info("Stopping the inference...")
        g.inference_cancelled = True

    if g.inference_session:
        g.inference_session.stop_async_inference()

    if g.inference_request_uuid:
        g.api.task.send_request(
            state["sessionId"],
            "stop_inference",
            data={"inference_request_uuid": g.inference_request_uuid},
        )


def annotations_to_video_annotation(
    frame_to_annotation: dict, obj_classes: sly.ObjClassCollection, video_shape: tuple
):
    name2vid_obj_cls = {x.name: sly.VideoObject(x) for x in obj_classes}
    video_obj_classes = sly.VideoObjectCollection(list(name2vid_obj_cls.values()))
    frames = []

    for idx, ann in output_data_widget.current_video_progress(
        frame_to_annotation.items(), message="Processing annotation"
    ):
        ann: sly.Annotation
        figures = []
        for label in ann.labels:
            vid_obj = name2vid_obj_cls[label.obj_class.name]
            vid_fig = sly.VideoFigure(vid_obj, label.geometry, idx)
            figures.append(vid_fig)
        frames.append(sly.Frame(idx, figures))
    frames_coll = sly.FrameCollection(frames)
    video_ann = sly.VideoAnnotation(video_shape, len(frames_coll), video_obj_classes, frames_coll)
    sly.logger.info(f"Annotation has been processed: {len(frame_to_annotation)} frames")
    return video_ann
