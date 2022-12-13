import os
import time

import cv2
import yaml
from fastapi import Depends
from tqdm import tqdm

import ffmpeg

import supervisely as sly

import deep_sort.sly_tracker as deep_sort_tracker
import deep_sort.sly_ann_keeper as deep_sort_ann_keeper

from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import src.sly_globals as g


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
    remote_video_path = os.path.join("ApplyNNtoVideosProject", "preview.mp4")
    if g.api.file.exists(g.team_id, remote_video_path):
        g.api.file.remove(g.team_id, remote_video_path)

    file_info = g.api.file.upload(g.team_id, local_video_path, remote_video_path, progress_cb=pbar_cb)
    return file_info


def generate_video_from_frames(preview_frames_path):
    local_preview_video_path = os.path.join(g.preview_frames_path, 'preview.mp4')
    if os.path.isfile(local_preview_video_path) is True:
        os.remove(local_preview_video_path)

    cmd_str = f'ffmpeg -f image2 -i {preview_frames_path}/frame%06d.png -c:v libx264 {local_preview_video_path}'

    os.system(cmd_str)

    for file in os.listdir(preview_frames_path):
        if file.endswith('.png'):
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

    DataJson()[f'done{step_num}'] = True
    state[f'collapsed{next_step}'] = False
    state[f'disabled{next_step}'] = False
    state['activeStep'] = next_step

    state['restartFrom'] = None

    run_sync(DataJson().synchronize_changes())
    run_sync(state.synchronize_changes())


def videos_to_frames(video_path, frames_range=None):
    def check_rotation(path_video_file):
        # this returns meta-data of the video file in form of a dictionary
        meta_dict = ffmpeg.probe(path_video_file)

        # from the dictionary, meta_dict['streams'][0]['tags']['rotate'] is the key
        # we are looking for
        rotate_code = None
        try:
            if int(meta_dict['streams'][0]['tags']['rotate']) == 90:
                rotate_code = cv2.ROTATE_90_CLOCKWISE
            elif int(meta_dict['streams'][0]['tags']['rotate']) == 180:
                rotate_code = cv2.ROTATE_180
            elif int(meta_dict['streams'][0]['tags']['rotate']) == 270:
                rotate_code = cv2.ROTATE_90_COUNTERCLOCKWISE
        except Exception as ex:
            pass

        return rotate_code

    def correct_rotation(frame, rotate_code):
        return cv2.rotate(frame, rotate_code)

    video_name = (video_path.split('/')[-1]).split('.mp4')[0]
    output_path = os.path.join(g.temp_dir, f'converted_{time.time_ns()}_{video_name}')

    os.makedirs(output_path, exist_ok=True)

    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    count = 0
    rotateCode = check_rotation(video_path)

    while success:
        if frames_range:
            if frames_range[0] <= count <= frames_range[1]:
                if rotateCode is not None:
                    image = correct_rotation(image, rotateCode)
                cv2.imwrite(f"{output_path}/frame{count:06d}.jpg", image)  # save frame as JPEG file
        else:
            if rotateCode is not None:
                image = correct_rotation(image, rotateCode)
            cv2.imwrite(f"{output_path}/frame{count:06d}.jpg", image)  # save frame as JPEG file

        success, image = vidcap.read()
        count += 1

    fps = vidcap.get(cv2.CAP_PROP_FPS)

    return {'frames_path': output_path, 'fps': fps, 'video_path': video_path}


def download_video(video_id, frames_range=None):
    video_info = g.api.video.get_info_by_id(video_id)
    save_path = os.path.join(g.temp_dir, f'{time.time_ns()}_{video_info.name}')

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
        cv2.imwrite(frame_path, img_rgb)  # save frame as PNG file

        frame_to_image_path[frame_index] = frame_path

        if pbar_cb is not None:
            pbar_cb()

    return frame_to_image_path


def get_annotation_keeper(ann_data, video_frames_path, frames_count):
    obj_id_to_object_class = deep_sort_ann_keeper.get_obj_id_to_obj_class(ann_data)
    video_shape = deep_sort_ann_keeper.get_video_shape(video_frames_path)

    ann_keeper = deep_sort_ann_keeper.AnnotationKeeper(video_shape=(video_shape[1], video_shape[0]),
                                                       obj_id_to_object_class=obj_id_to_object_class,
                                                       video_frames_count=frames_count)

    return ann_keeper


def draw_labels_on_frames(frames_to_image_path, frame_to_annotation):
    frames_indexes = list(frames_to_image_path.keys())

    for frame_index in frames_indexes:
        img_rgb = cv2.imread(frames_to_image_path[frame_index])
        img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)

        frame_to_annotation[frame_index].draw_contour(img_rgb, thickness=4)

        cv2.imwrite(frames_to_image_path[frame_index], img_rgb)


def get_model_inference(state, video_id, frames_range):
    try:
        inf_setting = yaml.safe_load(state["modelSettings"])
    except Exception as e:
        inf_setting = {}
        sly.logger.warn(f'Model Inference launched without additional settings. \n'
                        f'Reason: {e}', exc_info=True)

    return g.api.task.send_request(state['sessionId'], "inference_video_id",
                                   data={
                                       'videoId': video_id,
                                       'startFrameIndex': frames_range[0],
                                       'framesCount': frames_range[1] - frames_range[0] + 1,
                                       'settings': inf_setting
                                   }, timeout=60 * 60 * 24)['ann']


def apply_tracking_algorithm_to_predictions(state, video_id, frames_range, frame_to_annotation,
                                            tracking_algorithm='deepsort', pbar_cb=None) -> sly.VideoAnnotation:
    sly.logger.info(f'Applying tracking algorithm to predictions')

    video_local_info = download_video(video_id=video_id, frames_range=frames_range)
    video_remote_info = g.api.video.get_info_by_id(video_id)

    if tracking_algorithm == 'deepsort':
        opt = deep_sort_tracker.init_opt(state, frames_path=video_local_info['frames_path'])

        tracker_predictions = deep_sort_tracker.track(opt=opt, frame_to_annotation=frame_to_annotation, pbar_cb=pbar_cb)

        ann_keeper = get_annotation_keeper(tracker_predictions,
                                           video_frames_path=video_local_info['frames_path'],
                                           frames_count=video_remote_info.frames_count)
        ann_keeper.add_figures_by_frames(tracker_predictions)
        annotations: sly.VideoAnnotation = ann_keeper.get_annotations()
        return annotations
    else:
        raise NotImplementedError(f'Tracking algorithm {tracking_algorithm} is not implemented yet')


def frame_index_to_annotation(annotation_predictions, frames_range):
    frame_index_to_annotation_dict = {}

    for frame_index, annotation_json in zip(range(frames_range[0], frames_range[1] + 1), annotation_predictions):
        frame_index_to_annotation_dict[frame_index] = sly.Annotation.from_json(annotation_json, g.model_meta)

    return frame_index_to_annotation_dict


def get_video_size(local_video_path):
    return os.path.getsize(local_video_path)
