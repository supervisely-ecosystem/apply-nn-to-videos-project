import os
from pathlib import Path
import numpy as np
import yaml
from PIL import Image
from boxmot.utils import ROOT, WEIGHTS, TRACKER_CONFIGS
from boxmot import ByteTrack, BotSort
import supervisely as sly

from src.video import video_to_frames_ffmpeg


def apply_boxmot(
        api: sly.Api,
        video_id: int,
        frame_shape: tuple,
        frame_to_annotation: dict,
        device: str,
        work_dir: str,
        model_meta: sly.ProjectMeta,
        progress,
    ):
    video_path = f"{work_dir}/video.mp4"
    frames_dir = f"{Path(video_path).parent}/frames"
    sly.fs.remove_dir(frames_dir)
    name2cat = {x.name: i for i, x in enumerate(model_meta.obj_classes)}
    cat2obj = {i: obj for i, obj in enumerate(model_meta.obj_classes)}

    # Download video, break to frames
    api.video.download_path(video_id, video_path)
    video_to_frames_ffmpeg(video_path, frames_dir)
    img_paths = sorted(Path(frames_dir).glob("*.jpg"), key=lambda x: x.name)

    # Track
    tracker = load_tracker(tracker_type="botsort", device=device)
    results = []
    for i, ann in frame_to_annotation.items():
        img = Image.open(img_paths[i])
        detections = ann_to_detections(ann, name2cat)  # N x (x, y, x, y, conf, cls)
        tracks = tracker.update(detections, np.asarray(img))  # M x (x, y, x, y, track_id, conf, cls, det_id)
        results.append(tracks)
        progress.update(1)

    # Create VideoAnnotation
    video_ann = create_video_annotation(frame_to_annotation, results, frame_shape, cat2obj)
    return video_ann


def load_tracker(tracker_type: str, device: str, half: bool = False, per_class: bool = False):
    if "cuda" in device and ":" not in device:
        device = "cuda:0"

    tracker_config = TRACKER_CONFIGS / (tracker_type + '.yaml')

    # Load configuration from file
    with open(tracker_config, "r") as f:
        yaml_config = yaml.load(f, Loader=yaml.FullLoader)
        tracker_args = {param: details['default'] for param, details in yaml_config.items()}
    tracker_args['per_class'] = per_class

    reid_weights = '~/.cache/supervisely/checkpoints/osnet_x1_0_msmt17.pt'
    if device == 'cpu':
        reid_weights = '~/.cache/supervisely/checkpoints/osnet_x0_5_msmt17.pt'
    reid_weights = os.path.expanduser(reid_weights)

    reid_args = {
        'reid_weights': Path(reid_weights),
        'device': device,
        'half': half,
    }

    if tracker_type == 'bytetrack':
        tracker = ByteTrack(**tracker_args)
    elif tracker_type == 'botsort':
        tracker_args.update(reid_args)
        tracker = BotSort(**tracker_args)
    if hasattr(tracker, 'model'):
        tracker.model.warmup()
    return tracker


def ann_to_detections(ann: sly.Annotation, cls2label: dict):
    # convert ann to N x (x, y, x, y, conf, cls) np.array
    detections = []
    for label in ann.labels:
        cat = cls2label[label.obj_class.name]
        bbox = label.geometry.to_bbox()
        conf = label.tags.get("confidence").value
        detections.append([bbox.left, bbox.top, bbox.right, bbox.bottom, conf, cat])
    detections = np.array(detections)
    return detections


def create_video_annotation(
        frame_to_annotation: dict,
        tracking_results: list,
        frame_shape: tuple,
        cat2obj: dict,      
    ):
    img_h, img_w = frame_shape
    video_objects = {}  # track_id -> VideoObject
    frames = []
    for (i, ann), tracks in zip(frame_to_annotation.items(), tracking_results):
        frame_figures = []
        for track in tracks:
            # crop bbox to image size
            dims = np.array([img_w, img_h, img_w, img_h]) - 1
            track[:4] = np.clip(track[:4], 0, dims)
            x1, y1, x2, y2, track_id, conf, cat = track[:7]
            cat = int(cat)
            track_id = int(track_id)
            rect = sly.Rectangle(y1, x1, y2, x2)
            video_object = video_objects.get(track_id)
            if video_object is None:
                obj_cls = cat2obj[cat]
                video_object = sly.VideoObject(obj_cls)
                video_objects[track_id] = video_object
            frame_figures.append(sly.VideoFigure(video_object, rect, i))
        frames.append(sly.Frame(i, frame_figures))

    objects = list(video_objects.values())
    video_ann = sly.VideoAnnotation(
        img_size=frame_shape,
        frames_count=len(frame_to_annotation),
        objects=sly.VideoObjectCollection(objects),
        frames=sly.FrameCollection(frames),
    )
    return video_ann