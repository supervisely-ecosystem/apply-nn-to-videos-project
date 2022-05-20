### some card functional

def restart(data, state):
    data['done4'] = False


def get_videos_info(project_id):
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

    fields = [
        {"field": f"state.framesMin", "payload": frames_min},
        {"field": f"state.framesMax", "payload": frames_max},
    ]
    g.api.task.set_fields(g.task_id, fields)

    return general_videos_info


def generate_rows(project_ids):
    rows = []
    for project_id in project_ids:
        rows.extend(get_videos_info(project_id))

    return rows


def fill_table(table_rows):
    selected_videos = [row['name'] for row in table_rows if not row['isDisabled']] #@TODO: all selected in table
    fields = [
        {"field": f"state.statsLoaded", "payload": True},
        {"field": f"state.selectedVideos", "payload": selected_videos},
        {"field": f"data.videosTable", "payload": table_rows, "recursive": False},
    ]
    g.api.task.set_fields(g.task_id, fields)

    return 0