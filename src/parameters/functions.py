import supervisely as sly

import cv2
import os
import random
import src.sly_globals as g
import src.sly_functions as f
from supervisely.app import DataJson

import src.parameters.widgets as card_widgets


def restart(data, state):
    data["done5"] = False


def get_video_for_preview(state):
    videos_table = DataJson()["videosTable"]
    selected_videos = state['selectedVideos']

    frames_min = state['framesMin']
    frames_max = state['framesMax']

    random.shuffle(selected_videos)
    video_name = selected_videos[0]

    video_info = [row for row in videos_table if row['name'] == video_name][0]
    
    start_frame = 0
    if frames_max[video_info['name']] <= 30:
        end_frame = frames_max[video_info['name']]
    else:
        end_frame = frames_max[video_info['name']] + 1
        while end_frame > frames_max[video_info['name']]:
            start_frame = random.randint(frames_min[video_info['name']], frames_max[video_info['name']])
            end_frame = start_frame + 29


    dst_path = '/apply-nn-to-videos/preveiw-video/'
    if g.api.file.dir_exists(g.team_id, dst_path):
        g.api.file.remove(g.team_id, dst_path)
    

    return video_info, (start_frame, end_frame)


def get_preview_video(video_info, frame_to_annotation, frames_range):

    with card_widgets.preview_progress(message='Downloading Frames', total=abs(frames_range[0] - frames_range[1]) + 1) as progress:
        frames_to_image_path = f.download_frames_range(video_info, g.preview_frames_path, frames_range, pbar_cb=progress.update)


    with card_widgets.preview_progress(message='Generating Preview', total=1) as progress:
        f.draw_labels_on_frames(frames_to_image_path, frame_to_annotation)
        local_video_path = f.generate_video_from_frames(g.preview_frames_path)
        progress.update(1)

    # with card_widgets.preview_progress(message='Uploading Video', total=f.get_video_size(local_video_path), unit='B', unit_scale=True) as progress:
    with card_widgets.preview_progress(message='Uploading Video', total=1) as progress:
        preview_video_info = f.upload_video_to_sly(local_video_path)

    return preview_video_info.storage_path
