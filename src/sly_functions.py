import os
import time
from contextlib import contextmanager

import cv2
import yaml
import ffmpeg

import supervisely as sly

# from supervisely.nn.tracker import DeepSortTracker, BoTTracker

from supervisely.app.widgets import SlyTqdm
from supervisely.app import DataJson, StateJson
from supervisely.app.fastapi import run_sync
from supervisely.nn.inference import SessionJSON, Session

from supervisely.video_annotation.frame import Frame, VideoObjectCollection
from supervisely.video_annotation.frame_collection import FrameCollection

import src.sly_globals as g
import src.functions as f
from src.legacy_inference import legacy_inference_video, legacy_inference_video_async


def filter_annotation_by_classes(annotation_predictions: dict, selected_classes: list) -> dict:
    annotation_for_frame: sly.Annotation
    for frame_name, annotation_for_frame in annotation_predictions.items():
        filtered_labels_list = []

        for label_on_frame in annotation_for_frame.labels:
            if label_on_frame.obj_class.name in selected_classes:
                filtered_labels_list.append(label_on_frame)

        annotation_predictions[frame_name] = annotation_for_frame.clone(labels=filtered_labels_list)
    return annotation_predictions


def upload_video_to_sly(local_video_path, pbar_cb=None):
    remote_video_path = "/ApplyNNtoVideosProject/preview.mp4"
    if g.api.file.exists(g.team_id, remote_video_path):
        g.api.file.remove(g.team_id, remote_video_path)

    file_info = g.api.file.upload(
        g.team_id, local_video_path, f"/{remote_video_path}", progress_cb=pbar_cb
    )
    return file_info


def generate_video_from_frames(preview_frames_path):
    local_preview_video_path = os.path.join(g.preview_frames_path, "preview.mp4")
    if os.path.isfile(local_preview_video_path) is True:
        os.remove(local_preview_video_path)

    cmd_str = f"ffmpeg -f image2 -i {preview_frames_path}/frame%06d.png -c:v libx264 {local_preview_video_path}"

    os.system(cmd_str)

    for file in os.listdir(preview_frames_path):
        if file.endswith(".png"):
            os.remove(os.path.join(preview_frames_path, file))

    return local_preview_video_path


def get_files_paths(src_dir, extensions):
    files_paths = []
    for root, dirs, files in os.walk(src_dir):
        for extension in extensions:
            for file in files:
                if file.endswith(extension):
                    file_path = os.path.join(root, file)
                    files_paths.append(file_path)

    return files_paths


def finish_step(step_num, state, next_step=None):
    if next_step is None:
        next_step = step_num + 1

    DataJson()[f"done{step_num}"] = True
    state[f"collapsed{next_step}"] = False
    state[f"disabled{next_step}"] = False
    state["activeStep"] = next_step

    state["restartFrom"] = None

    run_sync(DataJson().synchronize_changes())
    run_sync(state.synchronize_changes())


def videos_to_frames(video_path, frames_range=None):
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_path = os.path.join(g.temp_dir, f"converted_{time.time_ns()}_{video_name}")

    os.makedirs(output_path, exist_ok=True)

    vidcap = cv2.VideoCapture(video_path)
    vidcap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    success, image = vidcap.read()
    count = 0

    while success:
        if frames_range:
            if frames_range[0] <= count <= frames_range[1]:
                cv2.imwrite(f"{output_path}/frame{count:06d}.jpg", image)  # save frame as JPEG file
        else:
            cv2.imwrite(f"{output_path}/frame{count:06d}.jpg", image)  # save frame as JPEG file

        success, image = vidcap.read()
        count += 1

    fps = vidcap.get(cv2.CAP_PROP_FPS)

    return {"frames_path": output_path, "fps": fps, "video_path": video_path}


def download_video(video_id, frames_range=None):
    video_info = g.api.video.get_info_by_id(video_id)
    save_path = os.path.join(g.temp_dir, f"{time.time_ns()}_{video_info.name}")

    if os.path.isfile(save_path):
        os.remove(save_path)

    g.api.video.download_path(video_id, save_path)
    return videos_to_frames(save_path, frames_range)


def download_frames_range(video_id, frames_dir_path, frames_range, pbar_cb=None):
    os.makedirs(frames_dir_path, exist_ok=True)
    sly.fs.clean_dir(frames_dir_path)

    frame_to_image_path = {}

    for index, frame_index in enumerate(range(frames_range[0], frames_range[1] + 1)):
        frame_path = os.path.join(f"{frames_dir_path}", f"frame{index:06d}.png")

        img_rgb = g.api.video.frame.download_np(video_id, frame_index)
        sly.image.write(frame_path, img_rgb)  # save frame as PNG file

        frame_to_image_path[frame_index] = frame_path

        if pbar_cb is not None:
            pbar_cb()

    return frame_to_image_path


# def get_annotation_keeper(ann_data, video_frames_path, frames_count):
#     obj_id_to_object_class = deep_sort_ann_keeper.get_obj_id_to_obj_class(ann_data)
#     video_shape = deep_sort_ann_keeper.get_video_shape(video_frames_path)

#     ann_keeper = deep_sort_ann_keeper.AnnotationKeeper(
#         video_shape=(video_shape[1], video_shape[0]),
#         obj_id_to_object_class=obj_id_to_object_class,
#         video_frames_count=frames_count,
#     )

#     return ann_keeper


def draw_labels_on_frames(frames_to_image_path, frame_to_annotation):
    frames_indexes = list(frames_to_image_path.keys())

    for frame_index in frames_indexes:
        img_rgb = cv2.imread(frames_to_image_path[frame_index])
        img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)

        frame_to_annotation[frame_index].draw_contour(img_rgb, thickness=4)

        sly.image.write(frames_to_image_path[frame_index], img_rgb)


@contextmanager
def can_stop():
    StateJson()["canStop"] = True
    StateJson().send_changes()
    try:
        yield
    finally:
        StateJson()["canStop"] = False
        StateJson().send_changes()


def on_inference_stop():
    # reverting UI to starting state
    DataJson()["annotatingStarted"] = False
    run_sync(DataJson().synchronize_changes())


def get_model_inference(state, video_id, frames_range, progress_widget: SlyTqdm = None):
    try:
        inf_setting, _ = f.get_model_and_tracking_settings(state)
    except Exception as e:
        inf_setting = {}
        sly.logger.warn(
            f"Model Inference launched without additional settings. \n" f"Reason: {e}",
            exc_info=True,
        )

    task_id = state["sessionId"]
    startFrameIndex = frames_range[0]
    framesCount = frames_range[1] - frames_range[0] + 1

    sly.logger.debug("Starting inference...")
    result = None

    if g.model_info.get("async_video_inference_support") is True:
        try:
            # serving versions 6.69.53+
            with can_stop():
                # Running async inference
                g.inference_session = SessionJSON(g.api, task_id, inference_settings=inf_setting)
                iterator = g.inference_session.inference_video_id_async(
                    video_id, startFrameIndex, framesCount, preparing_cb=progress_widget
                )
                result = list(progress_widget(iterator, message="Inferring model..."))

        except Exception as exc:
            # Fallback for serving versions: [6.69.15, 6.69.53)
            sly.logger.warn("Error in async video inference.", exc_info=True)
            sly.logger.warn("Trying legacy method...")
            g.inference_session = None
            with can_stop():
                result = legacy_inference_video_async(
                    task_id, video_id, startFrameIndex, framesCount, inf_setting, progress_widget
                )
    else:
        # Fallback to sync version (serving below 6.69.15)
        result = legacy_inference_video(
            task_id, video_id, startFrameIndex, framesCount, inf_setting, progress_widget
        )

    if g.inference_cancelled:
        on_inference_stop()
        progress_widget(message="", total=1)
        raise RuntimeError("The inference has been stopped by user.")

    if not result:
        raise RuntimeError(f"Empty result: {result}")

    if isinstance(result, dict) and "ann" in result.keys():
        result = result["ann"]

    sly.logger.info(f"Inference done! Result has {len(result)} items")
    return result


# def apply_tracking_algorithm_to_predictions(
#     state, video_id, frames_range, frame_to_annotation, tracking_algorithm="bot", pbar_cb=None
# ) -> sly.VideoAnnotation:
#     sly.logger.info(f"Applying tracking algorithm to predictions")

#     video_local_info = download_video(video_id=video_id, frames_range=frames_range)
#     video_remote_info = g.api.video.get_info_by_id(video_id)

#     if tracking_algorithm == "deepsort":
#         tracker = DeepSortTracker(state)
#     elif tracking_algorithm == "bot":
#         default_tracking_settings = {
#             "track_high_thresh": 0.4,
#             "track_low_thresh": 0.1,
#             "new_track_thresh": 0.5,
#             "match_thresh": 0.6,
#         }
#         tracker = BoTTracker(
#             {
#                 **default_tracking_settings,
#                 **state,
#             }
#         )
#     else:
#         raise NotImplementedError(f"Tracking algorithm {tracking_algorithm} is not implemented yet")

#     frames_path = video_local_info["frames_path"]
#     image_paths = sorted(get_files_paths(frames_path, [".png", ".jpg", ".jpeg"]))

#     return tracker.track(
#         image_paths,
#         frame_to_annotation,
#         (video_remote_info.frame_height, video_remote_info.frame_width),
#         pbar_cb=pbar_cb,
#     )


def frame_index_to_annotation(annotation_predictions, frames_range):
    frame_index_to_annotation_dict = {}

    for frame_index, annotation_json in zip(
        range(frames_range[0], frames_range[1] + 1), annotation_predictions
    ):
        if isinstance(annotation_json, dict) and "annotation" in annotation_json.keys():
            annotation_json = annotation_json["annotation"]
        frame_index_to_annotation_dict[frame_index] = sly.Annotation.from_json(
            annotation_json, g.model_meta
        )

    return frame_index_to_annotation_dict


def get_video_size(local_video_path):
    return os.path.getsize(local_video_path)


def track_on_model(
    state, video_id, frames_range, tracking_algorithm="boxmot", progress_widget: SlyTqdm = None
):
    if tracking_algorithm not in g.model_info.get("tracking_algorithms", []):
        raise ValueError(f"Tracking algorithm {tracking_algorithm} is not supported by the model")

    try:
        inf_setting, _ = f.get_model_and_tracking_settings(state)
    except Exception as e:
        inf_setting = {}
        sly.logger.warn(
            f"Model Inference launched without additional settings. \n" f"Reason: {e}",
            exc_info=True,
        )

    inf_setting["classes"] = g.selected_classes_list

    default_tracking_settings = {
        "track_high_thresh": 0.4,
        "track_low_thresh": 0.1,
        "new_track_thresh": 0.5,
        "match_thresh": 0.6,
    }
    for key, val in default_tracking_settings.items():
        inf_setting.setdefault(key, val)

    task_id = state["sessionId"]
    startFrameIndex = frames_range[0]
    framesCount = frames_range[1] - frames_range[0] + 1

    g.inference_session = Session(g.api, task_id, inference_settings=inf_setting)

    sly.logger.debug("Starting inference...")

    try:
        for _ in progress_widget(
            g.inference_session.inference_video_id_async(
                video_id,
                startFrameIndex,
                framesCount,
                tracker=tracking_algorithm,
            )
        ):
            pass
    except Exception:
        g.inference_session.stop_async_inference()
        raise

    result = g.inference_session.inference_result
    if result is None or result.get("video_ann", None) is None:
        raise RuntimeError("Model returned empty result")

    return result["video_ann"]
