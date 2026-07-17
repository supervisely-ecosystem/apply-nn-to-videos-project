import os
from pathlib import Path
import numpy as np
import yaml
from PIL import Image
from boxmot.utils import ROOT, WEIGHTS, TRACKER_CONFIGS
from boxmot import ByteTrack, BotSort
import supervisely as sly

from src.video import video_to_frames_ffmpeg


def get_boxmot_inference_classes(selected_classes, model_meta: sly.ProjectMeta):
    """Include pose bounding-box classes required internally by BoxMOT."""
    inference_classes = list(selected_classes)
    inference_class_names = set(inference_classes)
    for class_name in selected_classes:
        obj_class = model_meta.get_obj_class(class_name)
        if obj_class is None or obj_class.geometry_type is not sly.GraphNodes:
            continue
        bbox_class_name = f"{class_name}_bbox"
        bbox_class = model_meta.get_obj_class(bbox_class_name)
        if (
            bbox_class is not None
            and bbox_class.geometry_type is sly.Rectangle
            and bbox_class_name not in inference_class_names
        ):
            inference_classes.append(bbox_class_name)
            inference_class_names.add(bbox_class_name)
    return inference_classes


def apply_boxmot(
    api: sly.Api,
    video_id: int,
    frame_shape: tuple,
    frame_to_annotation: dict,
    device: str,
    work_dir: str,
    model_meta: sly.ProjectMeta,
    progress,
    tracking_settings,
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
    tracker = load_tracker(
        tracker_type="botsort", device=device, tracking_settings=tracking_settings
    )
    results = []
    detection_sources = []
    for i, ann in frame_to_annotation.items():
        img = Image.open(img_paths[i])
        detections, sources = ann_to_detections(
            ann, name2cat, frame_shape
        )  # N x (x, y, x, y, conf, cls)
        tracks = tracker.update(
            detections, np.asarray(img)
        )  # M x (x, y, x, y, track_id, conf, cls, det_id)
        results.append(tracks)
        detection_sources.append(sources)
        progress.update(1)

    # Create VideoAnnotation
    video_ann = create_video_annotation(
        frame_to_annotation,
        results,
        detection_sources,
        frame_shape,
        cat2obj,
    )
    return video_ann


def load_tracker(
    tracker_type: str,
    device: str,
    half: bool = False,
    per_class: bool = False,
    tracking_settings: dict = None,
):
    if "cuda" in device and ":" not in device:
        device = "cuda:0"

    tracker_config = TRACKER_CONFIGS / (tracker_type + ".yaml")

    # Load configuration from file
    with open(tracker_config, "r") as f:
        yaml_config = yaml.load(f, Loader=yaml.FullLoader)
        tracker_args = {param: details["default"] for param, details in yaml_config.items()}
        if tracking_settings is not None:
            tracker_args.update(tracking_settings)
    tracker_args["per_class"] = per_class

    reid_weights = "~/.cache/supervisely/checkpoints/osnet_x1_0_msmt17.pt"
    if device == "cpu":
        reid_weights = "~/.cache/supervisely/checkpoints/osnet_x0_5_msmt17.pt"
    reid_weights = os.path.expanduser(reid_weights)

    reid_args = {
        "reid_weights": Path(reid_weights),
        "device": device,
        "half": half,
    }

    if tracker_type == "bytetrack":
        tracker = ByteTrack(**tracker_args)
    elif tracker_type == "botsort":
        tracker_args.update(reid_args)
        tracker = BotSort(**tracker_args)
    if hasattr(tracker, "model"):
        tracker.model.warmup()
    return tracker


def _get_confidence(label: sly.Label):
    for tag_name in ("confidence", "conf"):
        confidence_tag = label.tags.get(tag_name)
        if confidence_tag is not None:
            confidence = float(confidence_tag.value)
            if np.isfinite(confidence):
                return confidence
    return None


def _bbox_iou(first: sly.Rectangle, second: sly.Rectangle) -> float:
    intersection_width = max(
        0.0, min(first.right, second.right) - max(first.left, second.left)
    )
    intersection_height = max(
        0.0, min(first.bottom, second.bottom) - max(first.top, second.top)
    )
    intersection = intersection_width * intersection_height
    union = first.area + second.area - intersection
    return intersection / union if union > 0 else 0.0


def _sanitize_graph_label(label: sly.Label, frame_shape: tuple):
    img_h, img_w = frame_shape
    valid_nodes = {}
    for node_id, node in label.geometry.nodes.items():
        row = float(node.location.row)
        col = float(node.location.col)
        is_top_left_placeholder = row <= 0 and col <= 0
        is_inside_frame = 0 <= row < img_h and 0 <= col < img_w
        if np.isfinite(row) and np.isfinite(col) and is_inside_frame:
            if not is_top_left_placeholder:
                valid_nodes[node_id] = node

    if len(valid_nodes) < 2:
        return None
    if len(valid_nodes) == len(label.geometry.nodes):
        return label
    return label.clone(geometry=sly.GraphNodes(valid_nodes))


def _find_companion_bbox(graph_index, graph_label, labels, used_bbox_indices):
    expected_class_name = f"{graph_label.obj_class.name}_bbox"

    # YOLO pose inference emits GraphNodes immediately before its companion box.
    next_index = graph_index + 1
    if next_index < len(labels):
        next_label = labels[next_index]
        if (
            next_index not in used_bbox_indices
            and isinstance(next_label.geometry, sly.Rectangle)
            and next_label.obj_class.name == expected_class_name
        ):
            return next_index, next_label

    graph_bbox = graph_label.geometry.to_bbox()
    best_match = None
    best_iou = 0.0
    for index, label in enumerate(labels):
        if (
            index in used_bbox_indices
            or not isinstance(label.geometry, sly.Rectangle)
            or label.obj_class.name != expected_class_name
        ):
            continue
        iou = _bbox_iou(graph_bbox, label.geometry)
        if iou > best_iou:
            best_iou = iou
            best_match = (index, label)
    return best_match


def ann_to_detections(ann: sly.Annotation, cls2label: dict, frame_shape: tuple):
    """Create one BoxMOT detection per output object and retain its source labels."""
    detections = []
    detection_sources = []
    labels = list(ann.labels)
    output_class_names = set(cls2label)
    used_bbox_indices = set()
    processed_graph_indices = set()

    for graph_index, label in enumerate(labels):
        if (
            label.obj_class.name not in output_class_names
            or not isinstance(label.geometry, sly.GraphNodes)
        ):
            continue

        graph_label = _sanitize_graph_label(label, frame_shape)
        if graph_label is None:
            sly.logger.debug(
                "Skipping pose detection with fewer than two valid keypoints",
                extra={"class_name": label.obj_class.name},
            )
            processed_graph_indices.add(graph_index)
            continue

        companion = _find_companion_bbox(
            graph_index, graph_label, labels, used_bbox_indices
        )
        confidence = _get_confidence(graph_label)
        detection_bbox = graph_label.geometry.to_bbox()
        source_labels = [graph_label]
        if companion is not None:
            bbox_index, bbox_label = companion
            bbox_confidence = _get_confidence(bbox_label)
            if bbox_confidence is not None:
                confidence = bbox_confidence
                detection_bbox = bbox_label.geometry
                used_bbox_indices.add(bbox_index)
                if bbox_label.obj_class.name in output_class_names:
                    source_labels.append(bbox_label)

        if confidence is None:
            sly.logger.debug(
                "Skipping pose detection without a confidence-bearing companion box",
                extra={"class_name": label.obj_class.name},
            )
            processed_graph_indices.add(graph_index)
            continue

        cat = cls2label[graph_label.obj_class.name]
        detections.append(
            [
                detection_bbox.left,
                detection_bbox.top,
                detection_bbox.right,
                detection_bbox.bottom,
                confidence,
                cat,
            ]
        )
        detection_sources.append(source_labels)
        processed_graph_indices.add(graph_index)

    for index, label in enumerate(labels):
        if (
            index in used_bbox_indices
            or index in processed_graph_indices
            or label.obj_class.name not in output_class_names
        ):
            continue

        confidence = _get_confidence(label)
        if confidence is None:
            sly.logger.debug(
                "Skipping detection without confidence",
                extra={"class_name": label.obj_class.name},
            )
            continue
        bbox = label.geometry.to_bbox()
        cat = cls2label[label.obj_class.name]
        detections.append(
            [bbox.left, bbox.top, bbox.right, bbox.bottom, confidence, cat]
        )
        detection_sources.append([label])

    return np.asarray(detections, dtype=np.float32).reshape((-1, 6)), detection_sources


def create_video_annotation(
    frame_to_annotation: dict,
    tracking_results: list,
    detection_sources: list,
    frame_shape: tuple,
    cat2obj: dict,
):
    img_h, img_w = frame_shape
    video_objects = {}  # (track_id, object class) -> VideoObject
    name2obj = {obj_class.name: obj_class for obj_class in cat2obj.values()}
    frames = []
    for (i, _), tracks, frame_sources in zip(
        frame_to_annotation.items(), tracking_results, detection_sources
    ):
        frame_figures = []
        for track in tracks:
            # crop bbox to image size
            dims = np.array([img_w, img_h, img_w, img_h]) - 1
            track[:4] = np.clip(track[:4], 0, dims)
            x1, y1, x2, y2, track_id, conf, cat = track[:7]
            cat = int(cat)
            track_id = int(track_id)
            det_id = int(track[7]) if len(track) > 7 else -1
            rect = sly.Rectangle(y1, x1, y2, x2)
            source_labels = (
                frame_sources[det_id]
                if 0 <= det_id < len(frame_sources)
                else []
            )

            if not source_labels:
                obj_cls = cat2obj.get(cat)
                if obj_cls is None or obj_cls.geometry_type is not sly.Rectangle:
                    continue
                source_labels = [None]

            for source_label in source_labels:
                if source_label is None:
                    obj_cls = cat2obj[cat]
                    geometry = rect
                else:
                    obj_cls = name2obj.get(source_label.obj_class.name)
                    if obj_cls is None:
                        continue
                    geometry = (
                        rect
                        if obj_cls.geometry_type is sly.Rectangle
                        else source_label.geometry
                    )
                    if not isinstance(geometry, obj_cls.geometry_type):
                        continue

                object_key = (track_id, obj_cls.name)
                video_object = video_objects.get(object_key)
                if video_object is None:
                    video_object = sly.VideoObject(obj_cls)
                    video_objects[object_key] = video_object
                frame_figures.append(sly.VideoFigure(video_object, geometry, i))
        frames.append(sly.Frame(i, frame_figures))

    objects = list(video_objects.values())
    video_ann = sly.VideoAnnotation(
        img_size=frame_shape,
        frames_count=len(frame_to_annotation),
        objects=sly.VideoObjectCollection(objects),
        frames=sly.FrameCollection(frames),
    )
    return video_ann
