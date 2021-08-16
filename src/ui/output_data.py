import supervisely_lib as sly
import sly_globals as g

from sly_progress import get_progress_cb, reset_progress, init_progress
from sly_progress import _update_progress_ui

_open_lnk_name = "open_app.lnk"


def init(data, state):
    init_progress("Videos", data)

    data['dstProjectId'] = None
    data['dstProjectName'] = None
    data['dstProjectPreviewUrl'] = None

    state["annotatingStarted"] = False

    state["collapsed6"] = True
    state["disabled6"] = True
    data["done6"] = False


def restart(data, state):
    data["done6"] = False


def init_project_remotely(project_name='ApplyNNtoVideoProject', ds_name='ds_0000'):
    project = g.api.project.create(g.workspace_id, project_name, type=sly.ProjectType.VIDEOS,
                                   change_name_if_conflict=True)

    dataset = g.api.dataset.create(project.id, f'{ds_name}',
                                   change_name_if_conflict=True)

    meta = g.model_meta  # @TODO generate meta for multiclass

    g.api.project.update_meta(project.id, meta.to_json())

    return project.id, dataset.id


def annotate_video(video_data):
    session_id = g.api.app.get_field(g.task_id, 'state.sessionId')
    conf_thres = g.api.app.get_field(g.task_id, 'state.confThres')

    frames_min = g.api.app.get_field(g.task_id, 'state.framesMin')
    frames_max = g.api.app.get_field(g.task_id, 'state.framesMax')

    video_id = video_data['videoId']
    frames_range = (frames_min[video_data['name']], frames_max[video_data['name']])

    result = g.api.task.send_request(session_id, "inference_video_id",
                                     data={'videoId': video_id,
                                           'framesRange': frames_range,
                                           'confThres': conf_thres,
                                           'isPreview': False}, timeout=60 * 60 * 24)  # temp solution

    return result['ann']


def upload_to_project(video_data, annotations, dataset_id):
    video_hash = video_data['videoHash']
    video_name = video_data['name']
    file_info = g.api.video.upload_hash(dataset_id, video_name, video_hash)

    annotations_sly = sly.VideoAnnotation.from_json(annotations, g.model_meta)

    g.api.video.annotation.append(file_info.id, annotations_sly)
    return 0


def annotate_videos():
    selected_videos_names = g.api.app.get_field(g.task_id, 'state.selectedVideos')
    video_progress = get_progress_cb("Videos", "Processing video", len(selected_videos_names), min_report_percent=1)

    output_project_name = g.api.app.get_field(g.task_id, 'state.expId')
    project_id, dataset_id = init_project_remotely(project_name=f'{output_project_name}',
                                                   ds_name=f'{g.model_info["app"]}')

    videos_table = g.api.app.get_field(g.task_id, 'data.videosTable')

    selected_videos_data = [row for row in videos_table if row['name'] in selected_videos_names]

    for video_data in selected_videos_data:
        try:
            annotations = annotate_video(video_data)
            upload_to_project(video_data, annotations, dataset_id)
            video_progress(1)

        except Exception as ex:
            raise RuntimeError(f'Error while processing: {video_data["name"]}:'
                               f'{ex}')

    reset_progress('Videos')

    res_project = g.api.project.get_info_by_id(project_id)
    fields = [{"field": "data.dstProjectId", "payload": res_project.id},
              {"field": "data.dstProjectName", "payload": res_project.name},
              {"field": "data.dstProjectPreviewUrl",
               "payload": g.api.image.preview_url(res_project.reference_image_url, 100, 100)},

              ]
    g.api.task.set_fields(g.task_id, fields)
    g.api.task.set_output_project(g.task_id, res_project.id, res_project.name)


@g.my_app.callback("start_annotation")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def start_annotation(api: sly.Api, task_id, context, state, app_logger):
    annotate_videos()

    fields = [
        {"field": "data.done6", "payload": True},
        {"field": "state.annotatingStarted", "payload": False},
    ]

    g.api.app.set_fields(g.task_id, fields)
