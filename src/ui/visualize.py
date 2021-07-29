import json
import os
import supervisely_lib as sly
from sly_visualize_progress import get_progress_cb, reset_progress, init_progress
import sly_globals as g

import sly_ann_keeper

from sly_visualize_progress import _update_progress_ui

from functools import partial

from lib.opts import opts
from sly_track_wrapper import main as track
from gen_data_path import gen_data_path
from gen_labels import gen_labels

import sys
import torch
import re
from PIL import Image

import shutil
import cv2

import glob

_open_lnk_name = "open_app.lnk"


def init(data, state):
    init_progress("Models", data)
    init_progress("Videos", data)
    init_progress("UploadDir", data)
    init_progress("UploadVideo", data)

    data["etaEpoch"] = None
    data["etaIter"] = None
    data["etaEpochData"] = []
    data['gridPreview'] = None

    data['dstProjectId'] = None
    data['dstProjectName'] = None
    data['dstProjectPreviewUrl'] = None

    state["visualizingStarted"] = False

    state["collapsed5"] = True
    state["disabled5"] = True
    state["done5"] = False

    data["outputName"] = None
    data["outputUrl"] = None


def restart(data, state):
    data["done5"] = False
    sly.fs.clean_dir(g.grid_video_dir)
    sly.fs.clean_dir(g.output_dir)


def init_script_arguments(state):
    sys.argv = []

    sys.argv.extend([f'task', 'mot'])

    def camel_to_snake(name):
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    needed_args = ['expId', 'gpus', 'confThres']

    for needed_arg in needed_args:
        sys.argv.extend([f'--{camel_to_snake(needed_arg)}', f'{state[needed_arg]}'])

    sys.argv.extend([f'--data_cfg', f'{g.my_app.data_dir}/sly_mot_generated.json'])
    sys.argv.extend([f'--output_format', ' video'])
    # sys.argv.extend([f'--output-root', '../demo_output/'])


def _save_link_to_ui(local_dir, app_url):
    # save report to file *.lnk (link to report)
    local_path = os.path.join(local_dir, _open_lnk_name)
    sly.fs.ensure_base_path(local_path)
    with open(local_path, "w") as text_file:
        print(app_url, file=text_file)


def upload_visualization_results():
    def upload_monitor(monitor, api: sly.Api, task_id, progress: sly.Progress):
        if progress.total == 0:
            progress.set(monitor.bytes_read, monitor.len, report=False)
        else:
            progress.set_current_value(monitor.bytes_read, report=False)
        _update_progress_ui("UploadDir", g.api, g.task_id, progress)

    progress = sly.Progress("Upload directory with visualization files to Team Files", 0, is_size=True)
    progress_cb = partial(upload_monitor, api=g.api, task_id=g.task_id, progress=progress)

    exp_id = g.api.app.get_field(g.task_id, 'state.expId')
    remote_dir = f"/FairMOT/visualization/{exp_id}"
    local_dir = os.path.join(g.output_dir, exp_id)

    _save_link_to_ui(local_dir, g.my_app.app_url)

    res_dir = g.api.file.upload_directory(g.team_id, local_dir, remote_dir, progress_size_cb=progress_cb)

    return res_dir


#
#
#
# def dump_info(state):
#     preview_pred_links = g.api.app.get_field(g.task_id, 'data.previewPredLinks')
#
#     sly.json.dump_json_file(state, os.path.join(g.info_dir, "ui_state.json"))
#     sly.json.dump_json_file(preview_pred_links,
#                             os.path.join(g.info, "preview_pred_links.json"))

def organize_in_mot_format(video_paths=None, is_train=True):
    organize_progress = get_progress_cb("VisualizeInfo", f"Organizing {'train' if is_train else 'validation'} data",
                                        (len(video_paths)))

    working_dir = 'train' if is_train else 'test'

    mot_general_dir = os.path.join(g.my_app.data_dir, 'data', 'SLY_MOT')
    mot_images_path = os.path.join(mot_general_dir, f'images/{working_dir}')
    os.makedirs(mot_images_path, exist_ok=True)

    for video_index, video_path in enumerate(video_paths):
        split_path = video_path.split('/')
        project_id = split_path[-3]
        ds_name = split_path[-2]

        destination = os.path.join(mot_images_path, f'{project_id}_{ds_name}_{video_index}')

        if not os.path.exists(destination):  # DEBUG
            shutil.copytree(video_path, destination)

        organize_progress(1)

    reset_progress("VisualizeInfo")


def get_visualizing_checkpoints(max_count):
    models_rows = g.api.app.get_field(g.task_id, 'data.modelsTable')
    selected_models = g.api.app.get_field(g.task_id, 'state.selectedModels')

    visualizing_models = []
    for row in models_rows:
        if row['name'] in selected_models:
            visualizing_models.append(row)

    visualizing_models = sorted(visualizing_models, key=lambda k: int(k['epoch']))

    if len(visualizing_models) <= max_count:
        return visualizing_models
    else:
        step = int(len(visualizing_models) / max_count)
        return [visualizing_models[index] for index in range(0, len(visualizing_models), step)][:max_count]


def get_visualization_video_paths(visualization_models):
    exp_id = g.api.app.get_field(g.task_id, 'state.expId')
    res_path = os.path.join(g.output_dir, exp_id)
    checkpoints_names = os.listdir(os.path.join(g.output_dir, exp_id))

    video_paths = []

    for visualization_model in visualization_models:
        folder_name = visualization_model['name'].replace('.', '_')
        if folder_name in checkpoints_names:
            videos_path = os.path.join(res_path, folder_name, 'videos')
            video_name = sorted(os.listdir(videos_path))[0]
            video_paths.append(os.path.join(videos_path, video_name))

    return video_paths


def get_video_shape(video_path):
    vcap = cv2.VideoCapture(video_path)
    height = width = 0
    if vcap.isOpened():
        width = vcap.get(3)  # float `width`
        height = vcap.get(4)

    return tuple([int(width), int(height)])


def check_video_shape(video_paths):
    video_shape = (0, 0)
    for index, video_path in enumerate(video_paths):
        if index == 0:
            video_shape = get_video_shape(video_path)
        else:
            if get_video_shape(video_path) != video_shape:
                return None
    return video_shape


def create_image_placeholder(video_shape):
    img = Image.new('RGB', video_shape, color='black')
    image_placeholder_path = os.path.join(g.grid_video_dir, 'placeholder.png')
    img.save(image_placeholder_path)


def generate_row(row_paths, videos_per_row):
    created_videos = glob.glob(f'{g.grid_video_dir}/*.mp4')
    video_num = len(created_videos)
    output_video_path = f'{g.grid_video_dir}/{video_num}.mp4'

    while len(row_paths) % videos_per_row != 0:  # filling empty grid space by placeholder
        row_paths.append(f'{g.grid_video_dir}/placeholder.png')

    if videos_per_row == 1:
        shutil.copy(row_paths[0], output_video_path)
    else:
        input_args = ' -i '.join(row_paths)

        cmd_str = f'ffmpeg -y -i {input_args} -filter_complex hstack={videos_per_row} -c:v libx264 {output_video_path}'
        # cmd_str = f'ffmpeg -y -i {input_args} -filter_complex "[0:v][1:v][2:v]hstack=inputs=3[v]" ' \
        #           f'-map "[v]" -c:v libx264 {output_video_path}'
        os.system(cmd_str)



def generate_grid():
    exp_id = g.api.app.get_field(g.task_id, 'state.expId')
    created_videos = sorted(glob.glob(f'{g.grid_video_dir}/*.mp4'))
    output_video_path = os.path.join(f'{g.output_dir}', f'{exp_id}', 'grid_preview.mp4')

    if len(created_videos) == 1:
        shutil.copy(created_videos[0], output_video_path)
    else:
        input_args = ' -i '.join(created_videos)

        cmd_str = f'ffmpeg -y -i {input_args} -filter_complex vstack={len(created_videos)} -c:v libx264 {output_video_path}'
        os.system(cmd_str)


def generate_grid_video(video_paths):
    video_shape = check_video_shape(video_paths)
    if video_shape:
        create_image_placeholder(video_shape)

        if len(video_paths) == 1:
            generate_row(video_paths, 1)
        elif len(video_paths) == 4:
            for index in range(0, len(video_paths), 2):
                row_paths = video_paths[index: index + 2]
                generate_row(row_paths, 2)
        else:
            for index in range(0, len(video_paths), 3):
                row_paths = video_paths[index: index + 3]
                generate_row(row_paths, 3)
        generate_grid()
        return 0
    else:
        return -1


def generate_preview_grid(count):
    checkpoints_list = get_visualizing_checkpoints(max_count=count)
    video_paths = get_visualization_video_paths(checkpoints_list)
    generate_grid_video(video_paths)


def get_visualized_checkpoints_paths():
    exp_name_folder = g.api.app.get_field(g.task_id, 'state.expId')
    results_path = os.path.join(g.output_dir, exp_name_folder)

    results_dirs = [potential_directory for potential_directory in
                    os.listdir(results_path) if os.path.isdir(os.path.join(results_path, potential_directory))]

    return [os.path.join(results_path, res_dir) for res_dir in results_dirs]


def get_objects_count(ann_path):
    objects_ids = []
    with open(ann_path, 'r') as ann_file:
        ann_rows = ann_file.read().split()

        for ann_row in ann_rows:
            objects_ids.append(ann_row.split(',')[1])

    return len(list(set(objects_ids)))


def get_objects_ids_to_indexes_mapping(ann_path):
    mapping = {}
    indexer = 0

    with open(ann_path, 'r') as ann_file:
        ann_rows = ann_file.read().split()

        for ann_row in ann_rows:
            curr_id = ann_row.split(',')[1]

            rc = mapping.get(curr_id, -1)
            if rc == -1:
                mapping[curr_id] = indexer
                indexer += 1

    return mapping


def get_coords_by_row(row_data, video_shape):
    left, top, w, h = float(row_data[2]), float(row_data[3]), \
                      float(row_data[4]), float(row_data[5])

    bottom = top + h
    if round(bottom) >= video_shape[1] - 1:
        bottom = video_shape[1] - 2
    right = left + w
    if round(right) >= video_shape[0] - 1:
        right = video_shape[0] - 2
    if left < 0:
        left = 0
    if top < 0:
        top = 0

    if right <= 0 or bottom <= 0 or left >= video_shape[0] or top >= video_shape[1]:
        return None
    else:
        return sly.Rectangle(top, left, bottom, right)


def add_figures_from_mot_to_sly(ann_path, ann_keeper, video_shape):
    ids_to_indexes_mapping = get_objects_ids_to_indexes_mapping(ann_path)

    with open(ann_path, 'r') as ann_file:
        ann_rows = ann_file.read().split()

    coords_on_frame = []
    objects_indexes_on_frame = []
    frame_index = None

    for ann_row in ann_rows:  # for each row in annotation
        row_data = ann_row.split(',')
        curr_frame_index = int(row_data[0]) - 1

        if frame_index is None:  # init first frame index
            frame_index = curr_frame_index

        if frame_index == curr_frame_index:  # if current frame equal previous
            object_coords = get_coords_by_row(row_data, video_shape=video_shape)
            if object_coords:
                coords_on_frame.append(object_coords)
                objects_indexes_on_frame.append(ids_to_indexes_mapping[row_data[1]])

        else:  # if frame has changed
            ann_keeper.add_figures_by_frame(coords_data=coords_on_frame,
                                            objects_indexes=objects_indexes_on_frame,
                                            frame_index=frame_index)

            coords_on_frame = []
            objects_indexes_on_frame = []

            frame_index = curr_frame_index
            object_coords = get_coords_by_row(row_data, video_shape=video_shape)
            if object_coords:
                coords_on_frame.append(object_coords)
                objects_indexes_on_frame.append(ids_to_indexes_mapping[row_data[1]])

    if frame_index:  # uploading latest annotations
        ann_keeper.add_figures_by_frame(coords_data=coords_on_frame,
                                        objects_indexes=objects_indexes_on_frame,
                                        frame_index=frame_index)


def process_video(video_path, ann_path, project_id=None, dataset_id=None):
    exp_id = g.api.app.get_field(g.task_id, 'state.expId')

    class_name = 'tracking object'
    objects_count = get_objects_count(ann_path)
    video_shape = get_video_shape(video_path)

    ann_keeper = sly_ann_keeper.AnnotationKeeper(video_shape=(video_shape[1], video_shape[0]),
                                                 objects_count=objects_count,
                                                 class_name=class_name)

    add_figures_from_mot_to_sly(ann_path=ann_path,
                                ann_keeper=ann_keeper,
                                video_shape=video_shape)

    ds_name = video_path.split('/')[-3]

    ann_keeper.init_project_remotely(project_id=project_id, ds_id=dataset_id,
                                     project_name=f'{exp_id} visualize', ds_name=f'{ds_name}')

    video_index = int(video_path.split('/')[-1].split('.mp4')[0])  # get original video path
    videos_data = g.api.app.get_field(g.task_id, 'data.videosData')
    origin_video_path = video_path
    for row in videos_data:
        if row['index'] == video_index:
            origin_video_path = row['origin_path']
            break

    ann_keeper.upload_annotation(video_path=origin_video_path)

    return ann_keeper.project.id, ann_keeper.dataset.id


def generate_sly_project():
    vis_paths = get_visualized_checkpoints_paths()
    video_extension = '.mp4'
    project_id = dataset_id = None

    models_progress = get_progress_cb('Models', "Upload checkpoint", len(vis_paths), min_report_percent=1)
    for vis_path in vis_paths:
        dataset_id = None

        videos_paths = g.get_files_paths(vis_path, video_extension)
        videos_progress = get_progress_cb('Videos', "Upload videos", len(videos_paths), min_report_percent=1)
        for video_path in videos_paths:
            ann_path = video_path.replace('videos', 'tracks').replace(video_extension, '.txt')
            if not os.path.isfile(ann_path):
                continue

            project_id, dataset_id = process_video(video_path,
                                                   ann_path,
                                                   project_id,
                                                   dataset_id)
            videos_progress(1)
        models_progress(1)

    reset_progress('Models')
    reset_progress('Videos')
    reset_progress('UploadVideo')

    res_project = g.api.project.get_info_by_id(project_id)
    fields = [{"field": "data.dstProjectId", "payload": res_project.id},
              {"field": "data.dstProjectName", "payload": res_project.name},
              {"field": "data.dstProjectPreviewUrl",
               "payload": g.api.image.preview_url(res_project.reference_image_url, 100, 100)},

              ]
    g.api.task.set_fields(g.task_id, fields)
    g.api.task.set_output_project(g.task_id, res_project.id, res_project.name)


@g.my_app.callback("visualize_videos")
@sly.timeit
@g.my_app.ignore_errors_and_show_dialog_window()
def visualize_videos(api: sly.Api, task_id, context, state, app_logger):
    sly_dir_path = os.getcwd()
    os.chdir('../../../src')
    try:

        init_script_arguments(state)

        opt = opts().init()
        # opt = opt.parse()

        track(opt)
        #
        generate_preview_grid(count=9)
        generate_sly_project()

        # hide progress bars and eta
        fields = [
            {"field": "data.progressModels", "payload": None},
            {"field": "data.progressVideos", "payload": None},
        ]
        g.api.app.set_fields(g.task_id, fields)

        remote_dir = upload_visualization_results()
        grid_file_info = api.file.get_info_by_path(g.team_id, os.path.join(remote_dir, 'grid_preview.mp4'))
        file_info = api.file.get_info_by_path(g.team_id, os.path.join(remote_dir, _open_lnk_name))

        api.task.set_output_directory(task_id, file_info.id, remote_dir)

        # show result directory in UI
        fields = [
            {"field": "data.gridPreview", "payload": grid_file_info.full_storage_url},
            {"field": "data.outputUrl", "payload": g.api.file.get_url(file_info.id)},
            {"field": "data.outputName", "payload": remote_dir},
            {"field": "data.done5", "payload": True},
            {"field": "state.visualizingStarted", "payload": False},
        ]
        # sly_train_renderer.send_fields({'data.eta': None})  # SLY CODE
        g.api.app.set_fields(g.task_id, fields)
    except Exception as e:
        api.app.set_field(task_id, "state.visualizingStarted", False)
        raise e  # app will handle this error and show modal window

    os.chdir(sly_dir_path)
    # stop application
    # g.my_app.stop()
