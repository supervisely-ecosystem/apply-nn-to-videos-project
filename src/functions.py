import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import numpy as np
import yaml
from PIL import Image

import supervisely as sly
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync
from supervisely import Project

import src.sly_globals as g
from src.ui.parameters.parameters import parameters_widget
from src.ui.output_data.output_data import output_data_widget
import src.workflow as w
from src.video import video_to_frames_ffmpeg
from src import boxmot_tracking


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
        state["modelSettings"] = g.api.task.send_request(
            session_id, "get_custom_inference_settings", data={}
        ).get("settings", None)
        if state["modelSettings"] is None or len(state["modelSettings"]) == 0:
            raise ValueError()
        elif isinstance(state["modelSettings"], dict):
            state["modelSettings"] = yaml.dump(state["modelSettings"], allow_unicode=True)
        sly.logger.info(f'Custom inference settings: {state["modelSettings"]}')
    except Exception as ex:
        state["modelSettings"] = ""
        sly.logger.info("Model doesn't support custom inference settings.\n" f"Reason: {repr(ex)}")


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

    datasets = g.api.dataset.get_list(project_id)
    g.ds_video_map = {}
    for ds in datasets:
        videos_info = g.api.video.get_list(ds.id)
        g.ds_video_map[ds.name] = []

        for video_info in videos_info:
            g.ds_video_map[ds.name].append(video_info.name)
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

    meta = g.model_meta  # @TODO generate meta for multiclass

    g.api.project.update_meta(project.id, meta.to_json())

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
                device = state["device"]
                work_dir = g.temp_dir
                video_path = f"{work_dir}/video.mp4"
                frames_dir = f"{Path(video_path).parent}/frames"
                img_h, img_w = video_data["frame_shape"]
                sly.fs.remove_dir(frames_dir)
                g.api.video.download_path(video_id, video_path)
                video_to_frames_ffmpeg(video_path, frames_dir)
                img_paths = sorted(Path(frames_dir).glob("*.jpg"), key=lambda x: x.name)
                tracker = boxmot_tracking.load_tracker(tracker_type="botsort", device=device)
                name2cat = {x.name: i for i, x in enumerate(g.model_meta.obj_classes)}
                cat2name = {c: n for n, c in name2cat.items()}
                cat2obj = {i: obj for i, obj in enumerate(g.model_meta.obj_classes)}

                # Track
                results = []
                for i, ann in frame_to_annotation.items():
                    img = Image.open(img_paths[i])
                    detections = boxmot_tracking.ann_to_detections(ann, name2cat)  # N x (x, y, x, y, conf, cls)
                    tracks = tracker.update(detections, np.asarray(img))  # M x (x, y, x, y, track_id, conf, cls, det_id)
                    results.append(tracks)
                    progress.update(1)

                # Create VideoAnnotation
                video_objects = {}  # track_id -> VideoObject
                frames = []
                for (i, ann), tracks in zip(frame_to_annotation.items(), results):
                    frame_figures = []
                    for track in tracks:
                        # crop bbox to image size
                        dims = np.array([img_w, img_h, img_w, img_h]) - 1e-5
                        track[:4] = np.clip(track[:4], 0, dims)
                        x1, y1, x2, y2, track_id, conf, cat = track[:7]
                        cat = int(cat)
                        track_id = int(track_id)
                        rect = sly.Rectangle(y1, x1, y2, x2)
                        video_object = video_objects.get(track_id)
                        if video_object is None:
                            obj_cls = cat2obj[cat]
                            video_object = sly.VideoObject(obj_cls)
                            video_objects[track_id] = video_object
                        frame_figures.append(sly.VideoFigure(video_object, rect, i))
                    frames.append(sly.Frame(i, frame_figures))

                objects = list(video_objects.values())
                video_ann = sly.VideoAnnotation(
                    img_size=video_data["frame_shape"],
                    frames_count=len(frame_to_annotation),
                    objects=sly.VideoObjectCollection(objects),
                    frames=sly.FrameCollection(frames),
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
        obj_classes = g.model_meta.obj_classes
        return annotations_to_video_annotation(
            frame_to_annotation, obj_classes, video_data["frame_shape"]
        )


def annotate_videos(state):
    selected_videos_names = state["selectedVideos"]

    w.workflow_input(g.api, project_id=g.project_id, session_id=state["sessionId"])
    output_project_name = state["expId"]
    project_id = init_project_remotely(project_name=output_project_name)

    for ds_name in g.ds_video_map:
        dataset = g.api.dataset.create(project_id, ds_name, change_name_if_conflict=True)

        videos_table = DataJson()["videosTable"]

        selected_videos_data = [
            row
            for row in videos_table
            if row["name"] in selected_videos_names
            and row["name"] in g.ds_video_map[ds_name]
            and row["dataset"] == ds_name
        ]

        for video_data in output_data_widget.apply_nn_to_video_project_progress(
            selected_videos_data, message=f"Inference Videos in dataset: {ds_name}"
        ):
            annotation: sly.VideoAnnotation = get_video_annotation(video_data, state)
            upload_to_project(
                video_data, annotation, dataset.id, output_data_widget.current_video_progress
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
