import os
from pathlib import Path
import numpy as np
import yaml
from boxmot.utils import ROOT, WEIGHTS, TRACKER_CONFIGS
from boxmot import ByteTrack, BotSort
import supervisely as sly



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