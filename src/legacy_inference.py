import src.sly_globals as g
import supervisely as sly
import time


def legacy_inference_video(task_id, video_id, startFrameIndex, framesCount, inference_setting, progress_widget):
    with progress_widget(message="Gathering Predictions from Model...", total=1) as pbar:
        result = g.api.task.send_request(
            task_id, 
            "inference_video_id",
            data={
                'videoId': video_id,
                'startFrameIndex': startFrameIndex,
                'framesCount': framesCount,
                'settings': inference_setting
            }, timeout=60 * 60 * 24
        )
        pbar.update(1)
    return result


def legacy_inference_video_async(task_id, video_id, startFrameIndex, framesCount, inference_setting, progress_widget):
    # serving versions: [6.69.15, 6.69.53)
    def get_inference_progress(inference_request_uuid):
        sly.logger.debug("Requesting inference progress...")
        result = g.api.task.send_request(
            task_id,
            "get_inference_progress",
            data={"inference_request_uuid": inference_request_uuid}
        )
        return result

    resp = g.api.task.send_request(
        task_id, 
        "inference_video_id_async",
        data={
            'videoId': video_id,
            'startFrameIndex': startFrameIndex,
            'framesCount': framesCount,
            'settings': inference_setting
        }
    )
    g.inference_request_uuid = resp["inference_request_uuid"]

    is_inferring = True
    pbar = None
    while is_inferring:
        progress = get_inference_progress(g.inference_request_uuid)
        current, total = progress['progress']['current'], progress['progress']['total']
        is_inferring = progress["is_inferring"]
        sly.logger.info(f"Inferring model... {current} / {total}")
        if pbar is None and total > 1:
            # The first time when we got `total`
            pbar = progress_widget(message="Inferring model...", total=total, initial=0)
        if pbar:
            pbar.update(current - pbar.n)
        time.sleep(1)
    result = progress["result"]

    return result
