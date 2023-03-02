### some card functional

import src.sly_globals as g
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync


def restart(data, state):
    data['done4'] = False


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
                {'name': video_info.name,
                 "dataset": ds.name,
                 "framesCount": video_info.frames_count,
                 "framesRange": "-",

                 "isDisabled": True if video_info.frames_count < 5 else False,

                 'videoId': video_info.id,
                 'videoHash': video_info.hash,
                 "frame_shape": (video_info.frame_height, video_info.frame_width)
                 }
            )

            frames_min[video_info.name] = 0
            frames_max[video_info.name] = video_info.frames_count - 1

    state['framesMin'] = frames_min
    state['framesMax'] = frames_max

    return general_videos_info


def generate_rows(project_id, state) -> list:
    return get_videos_info(project_id, state)


def fill_table(table_rows, state):
    selected_videos = [row['name'] for row in table_rows if not row['isDisabled']]

    state['statsLoaded'] = True
    state['selectedVideos'] = selected_videos

    DataJson()['videosTable'] = table_rows

    run_sync(DataJson().synchronize_changes())
    run_sync(state.synchronize_changes())
