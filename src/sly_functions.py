import os

import cv2
from fastapi import Depends
from tqdm import tqdm

import supervisely as sly

import src.sly_globals as g
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync


def filter_annotation_by_classes(annotation_predictions: dict, selected_classes: list) -> dict:
    annotation_for_frame: sly.Annotation
    for frame_name, annotation_for_frame in annotation_predictions.items():
        filtered_labels_list = []

        for label_on_frame in annotation_for_frame.labels:
            if label_on_frame.obj_class.name in selected_classes:
                filtered_labels_list.append(label_on_frame)

        annotation_predictions[frame_name] = annotation_for_frame.clone(labels=filtered_labels_list)
    return annotation_predictions


def upload_video_to_sly(local_video_path):
    remote_video_path = os.path.join("ApplyNNtoVideosProject", "preview.mp4")
    if g.api.file.exists(g.team_id, remote_video_path):
        g.api.file.remove(g.team_id, remote_video_path)

    file_info = g.api.file.upload(g.team_id, local_video_path, remote_video_path)
    return file_info


def generate_video_from_frames(preview_frames_path):
    local_preview_video_path = os.path.join(g.preview_frames_path, f'preview.mp4')
    if os.path.isfile(local_preview_video_path) is True:
        os.remove(local_preview_video_path)

    cmd_str = 'ffmpeg -f image2 -i {}/frame%06d.png -c:v libx264 {}'.format(preview_frames_path, local_preview_video_path)
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
    state[f'activeStep'] = next_step

    run_sync(DataJson().synchronize_changes())
    run_sync(state.synchronize_changes())


def download_frames_range(video_id, frames_dir_path, frames_range):
    os.makedirs(frames_dir_path, exist_ok=True)
    sly.fs.clean_dir(frames_dir_path)

    frame_to_image_path = {}

    for index, frame_index in tqdm(enumerate(range(frames_range[0], frames_range[1] + 1)), desc='Downloading frames'):
        frame_path = os.path.join(f"{frames_dir_path}", f"frame{index:06d}.png")

        img_rgb = g.api.video.frame.download_np(video_id, frame_index)
        cv2.imwrite(frame_path, img_rgb)  # save frame as PNG file

        frame_to_image_path[frame_index] = frame_path
    return frame_to_image_path



def get_annotation_from_predictions(annotation_predictions):
    for frame_name, annotation_json in annotation_predictions.items():
        annotation_for_frame = sly.Annotation.from_json(annotation_json, g.model_meta)
        filtered_labels_list = []

        figure = sly.VideoFigure()

    return None


def draw_labels_on_frames(frames_to_image_path, frame_to_annotation):
    frames_indexes = list(frames_to_image_path.keys())

    for frame_index in frames_indexes:
        img_rgb = cv2.imread(frames_to_image_path[frame_index])
        img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)

        frame_to_annotation[frame_index].draw(img_rgb)

        cv2.imwrite(frames_to_image_path[frame_index], img_rgb)
