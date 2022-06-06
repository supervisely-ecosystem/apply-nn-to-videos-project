import supervisely as sly

import random
import src.sly_globals as g
import src.sly_functions as f
from supervisely.app import DataJson


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
    end_frame = frames_max[video_info['name']] + 1
    while end_frame > frames_max[video_info['name']]:
        start_frame = random.randint(frames_min[video_info['name']], frames_max[video_info['name']])
        end_frame = start_frame + 29

    return video_info['videoId'], (start_frame, end_frame)


def apply_tracking_algorithm_to_predictions(predictions):

    pass





def get_preview_video(video_id, frame_to_annotation, frames_range):
    frames_to_image_path = f.download_frames_range(video_id, g.preview_frames_path, frames_range)
    f.draw_labels_on_frames(frames_to_image_path, frame_to_annotation)
    local_video_path = f.generate_video_from_frames(g.preview_frames_path)
    return f.upload_video_to_sly(local_video_path).full_storage_url