### some card functional

def restart(data, state):
    data["done5"] = False


def get_video_for_preview():
    videos_table = g.api.app.get_field(g.task_id, 'data.videosTable')
    selected_videos = g.api.app.get_field(g.task_id, 'state.selectedVideos')

    frames_min = g.api.app.get_field(g.task_id, 'state.framesMin')
    frames_max = g.api.app.get_field(g.task_id, 'state.framesMax')

    random.shuffle(selected_videos)
    video_name = selected_videos[0]

    video_info = [row for row in videos_table if row['name'] == video_name][0]

    start_frame = 0
    end_frame = frames_max[video_info['name']] + 1
    while end_frame > frames_max[video_info['name']]:
        start_frame = random.randint(frames_min[video_info['name']], frames_max[video_info['name']])
        end_frame = start_frame + 4

    return video_info['videoId'], (start_frame, end_frame)
