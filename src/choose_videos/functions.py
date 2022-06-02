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

    ds_ids = g.api.dataset.get_list(project_id)
    for ds_id in ds_ids:
        videos_info = g.api.video.get_list(ds_id.id)

        for video_info in videos_info:
            general_videos_info.append(
                {'name': f"[{ds_id.name}] {video_info.name}",
                 "dataset": ds_id.name,
                 "framesCount": video_info.frames_count,
                 "framesRange": "-",

                 "isDisabled": True if video_info.frames_count < 5 else False,

                 'videoId': video_info.id,
                 'videoHash': video_info.hash
                 }
            )

            frames_min[f"[{ds_id.name}] {video_info.name}"] = 0
            frames_max[f"[{ds_id.name}] {video_info.name}"] = video_info.frames_count - 1

    state['framesMin'] = frames_min
    state['framesMax'] = frames_max

    return general_videos_info


def generate_rows(project_ids, state) -> list:
    rows = []

    for project_id in project_ids:
        rows.extend(get_videos_info(project_id, state))

    return rows


def fill_table(table_rows, state):
    selected_videos = [row['name'] for row in table_rows if not row['isDisabled']]

    state['statsLoaded'] = True
    state['selectedVideos'] = selected_videos

    DataJson()['videosTable'] = table_rows

    run_sync(DataJson().synchronize_changes())
    run_sync(state.synchronize_changes())
