### some card functional
import yaml

import supervisely as sly

import src.sly_globals as g
import src.sly_functions as f

import src.output_data.widgets as card_widgets
from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync


def restart(data, state):
    data["done6"] = False


def shutdown_app():
    try:
        sly.app.fastapi.shutdown()
    except KeyboardInterrupt:
        sly.logger.info("Application shutdown successfully")


def init_project_remotely(project_name="ApplyNNtoVideoProject"):
    project = g.api.project.create(
        g.workspace_id,
        project_name,
        type=sly.ProjectType.VIDEOS,
        change_name_if_conflict=True,
    )

    meta = g.model_meta  # @TODO generate meta for multiclass

    g.api.project.update_meta(project.id, meta.to_json())

    return project.id


def upload_to_project(video_data, annotation: sly.VideoAnnotation, dataset_id):
    video_hash = video_data["videoHash"]
    video_name = video_data["name"]
    file_info = g.api.video.upload_hash(dataset_id, video_name, video_hash)

    g.api.video.annotation.append(file_info.id, annotation)


def get_video_annotation(video_data, state) -> sly.VideoAnnotation:
    frames_min = state["framesMin"]
    frames_max = state["framesMax"]
    frames_range = (frames_min[video_data["name"]], frames_max[video_data["name"]])

    model_predictions = f.get_model_inference(
        state, video_id=video_data["videoId"], frames_range=frames_range
    )

    frame_to_annotation = f.frame_index_to_annotation(model_predictions, frames_range)
    frame_to_annotation = f.filter_annotation_by_classes(
        frame_to_annotation, g.selected_classes_list
    )

    if state["applyTrackingAlgorithm"] is True:
        with card_widgets.current_video_progress(
            message=f'Applying tracking algorithm ({state["selectedTrackingAlgorithm"]})',
            total=abs(frames_range[0] - frames_range[1]) + 1,
        ) as progress:

            return f.apply_tracking_algorithm_to_predictions(
                state=state,
                video_id=video_data["videoId"],
                frames_range=frames_range,
                frame_to_annotation=frame_to_annotation,
                tracking_algorithm=state["selectedTrackingAlgorithm"],
                pbar_cb=progress.update,
            )
    else:
        raise NotImplementedError
        # return f.get_annotation_from_predictions(frame_to_annotation)


def annotate_videos(state):
    selected_videos_names = state["selectedVideos"]

    output_project_name = state["expId"]
    project_id = init_project_remotely(project_name=output_project_name)

    for ds_name in g.ds_video_map:
        dataset = g.api.dataset.create(
            project_id, ds_name, change_name_if_conflict=True
        )

        videos_table = DataJson()["videosTable"]

        selected_videos_data = [
            row
            for row in videos_table
            if row["name"] in selected_videos_names
            and row["name"] in g.ds_video_map[ds_name]
            and row["dataset"] == ds_name
        ]

        for video_data in card_widgets.apply_nn_to_video_project_progress(
            selected_videos_data, message=f"Inference Videos in dataset: {ds_name}"
        ):
            try:
                annotation: sly.VideoAnnotation = get_video_annotation(
                    video_data, state
                )
                upload_to_project(video_data, annotation, dataset.id)

            except Exception as ex:
                raise RuntimeError(
                    f'Error while processing: {video_data["name"]}:' f"{ex}"
                )

    res_project = g.api.project.get_info_by_id(project_id)
    DataJson().update(
        {
            "dstProjectId": res_project.id,
            "dstProjectName": res_project.name,
            "dstProjectPreviewUrl": g.api.image.preview_url(
                res_project.reference_image_url, 100, 100
            ),
        }
    )

    DataJson()["done6"] = True
    DataJson()["annotatingStarted"] = False

    run_sync(DataJson().synchronize_changes())
    shutdown_app()


def stop_annotate_videos(state):
    if g.inference_request_uuid:
        sly.logger.info("Stopping inference...")
        g.api.task.send_request(state['sessionId'], "stop_inference", data={"inference_request_uuid": g.inference_request_uuid})
        card_widgets.current_video_progress(message="Inferring model...", total=1)