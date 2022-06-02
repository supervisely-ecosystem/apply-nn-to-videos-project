### some card functional
import random
import src.sly_globals as g
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
        end_frame = start_frame + 4

    return video_info['videoId'], (start_frame, end_frame)
