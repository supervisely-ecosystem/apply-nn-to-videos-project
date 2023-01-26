import argparse
import sys

import clip
import cv2

import torch

import numpy as np

from deep_sort.utils.torch_utils import select_device

# deep sort imports
from deep_sort.deep_sort import preprocessing, nn_matching
from deep_sort.deep_sort.detection import Detection
from deep_sort.deep_sort.tracker import Tracker
from deep_sort.tools import generate_clip_detections as gdet


import src.sly_functions as f
import src.sly_globals as g

import supervisely as sly
from tqdm import tqdm


def init_opt(state, frames_path):
    parser = argparse.ArgumentParser(prog='deepsort_tracker')

    parser.add_argument('--device', type=str,
                        default=state['device'], help='device to process')
    parser.add_argument('--detection_threshold', type=float,
                        default=0,
                        help='threshold for detector model')
    parser.add_argument('--nms_max_overlap', type=float,
                        default=1.0,
                        help='Non-maxima suppression threshold: Maximum detection overlap.')
    parser.add_argument('--max_cosine_distance', type=float,
                        default=0.6,
                        help='Gating threshold for cosine distance metric (object appearance).')
    parser.add_argument('--nn_budget', type=int,
                        default=None,
                        help='Maximum size of the appearance descriptors allery. If None, no budget is enforced.')

    parser.add_argument('--thickness', type=int,
                        default=1, help='Thickness of the bounding box strokes')

    parser.add_argument('--info', action='store_true',
                        help='Print debugging info.')

    opt, _ = parser.parse_known_args()
    opt.source_path = frames_path

    return opt


def convert_annotation(annotation_for_frame: sly.Annotation):
    formatted_predictions = []
    classes = []
    sly_labels = []

    for label in annotation_for_frame.labels:
        confidence = 1.0
        if label.tags.get('confidence', None) is not None:
            confidence = label.tags.get('confidence').value
        elif label.tags.get('conf', None) is not None:
            confidence = label.tags.get('conf').value

        rectangle: sly.Rectangle = label.geometry.to_bbox()
        formatted_pred = [rectangle.left, rectangle.top, rectangle.right, rectangle.bottom, confidence]

        # convert to width / height
        formatted_pred[2] -= formatted_pred[0]
        formatted_pred[3] -= formatted_pred[1]

        formatted_predictions.append(formatted_pred)
        classes.append(label.obj_class.name)
        sly_labels.append(label)

    return formatted_predictions, classes, sly_labels


def correct_figure(img_size, figure):  # img_size — height, width tuple
    # check figure is within image bounds
    canvas_rect = sly.Rectangle.from_size(img_size)
    if canvas_rect.contains(figure.to_bbox()) is False:
        # crop figure
        figures_after_crop = [cropped_figure for cropped_figure in figure.crop(canvas_rect)]
        if len(figures_after_crop) > 0:
            return figures_after_crop[0]
        else:
            return None
    else:
        return figure


def update_track_data(tracks_data, tracks, frame_index, img_size):
    coordinates_data = []
    track_id_data = []
    labels_data = []

    for curr_track in tracks:
        if not curr_track.is_confirmed() or curr_track.time_since_update > 1:
            continue

        # tl_br = curr_track.to_tlbr()  # (!!!) LTRB
        # class_name = curr_track.class_num
        track_id = curr_track.track_id - 1  # tracks in deepsort started from 1
        # bbox = xyxy

        # potential_rectangle = sly.Rectangle(top=int(round(tl_br[1])),
        #                                     left=int(round(tl_br[0])),
        #                                     bottom=int(round(tl_br[3])),
        #                                     right=int(round(tl_br[2])))
        #
        # tested_rectangle = correct_figure(img_size, potential_rectangle)
        # if tested_rectangle:
        # coordinates_data.append(tested_rectangle)

        if curr_track.get_sly_label() is not None:
            track_id_data.append(track_id)
            labels_data.append(curr_track.get_sly_label())

    tracks_data[frame_index] = {'ids': track_id_data,
                                'labels': labels_data}

    return tracks_data


def clear_empty_ids(tracker_annotations):
    id_mappings = {}
    last_ordinal_id = 0

    for frame_index, data in tracker_annotations.items():
        data_ids_temp = []
        for current_id in data['ids']:
            new_id = id_mappings.get(current_id, -1)
            if new_id == -1:
                id_mappings[current_id] = last_ordinal_id
                last_ordinal_id += 1
                new_id = id_mappings.get(current_id, -1)
            data_ids_temp.append(new_id)
        data['ids'] = data_ids_temp

    return tracker_annotations


def track(opt, frame_to_annotation, pbar_cb=None):
    # @TODO: add save original geometry, not bbox only

    tracks_data = {}

    device = select_device(opt.device)

    nms_max_overlap = opt.nms_max_overlap
    max_cosine_distance = opt.max_cosine_distance
    nn_budget = opt.nn_budget
    # frame_index_mapping = opt.frame_indexes

    model_filename = "ViT-B/32"  # initialize deep sort
    sly.logger.info("Loading CLIP...")
    model, transform = clip.load(model_filename, device=device)
    encoder = gdet.create_box_encoder(model, transform, batch_size=1, device=device)

    metric = nn_matching.NearestNeighborDistanceMetric(  # calculate cosine distance metric
        "cosine", max_cosine_distance, nn_budget)

    tracker = Tracker(metric, n_init=1)  # initialize tracker

    source_path = opt.source_path

    image_paths = sorted(f.get_files_paths(source_path, ['.png', '.jpg', '.jpeg']))

    sly.logger.info("Starting CLIP tracking...")
    # frame_index = 0
    for frame_index in frame_to_annotation.keys():
        detections = []
        im0 = cv2.imread(image_paths[frame_index])
        
        try:
            pred, classes, sly_labels = convert_annotation(frame_to_annotation[frame_index])
            det = torch.tensor(pred)

            # Process detections
            bboxes = det[:, :4].clone().cpu()
            confs = det[:, 4]

            # encode yolo detections and feed to tracker
            features = encoder(im0, bboxes)
            detections = [Detection(bbox, conf, class_num, feature, sly_label) for bbox, conf, class_num, feature, sly_label in zip(
                bboxes, confs, classes, features, sly_labels)]

            # run non-maxima supression
            boxs = np.array([d.tlwh for d in detections])
            scores = np.array([d.confidence for d in detections])
            class_nums = np.array([d.class_num for d in detections])
            indices_of_alive_labels = preprocessing.non_max_suppression(boxs, class_nums, nms_max_overlap, scores)
            detections = [detections[i] for i in indices_of_alive_labels]
        except Exception as ex:
            import traceback
            sly.logger.info(f'frame {frame_index} skipped on tracking')
            sly.logger.debug(traceback.format_exc())
        
        # Call the tracker
        tracker.predict()
        tracker.update(detections)

        update_track_data(tracks_data=tracks_data,
                          tracks=tracker.tracks,
                          frame_index=frame_index,
                          img_size=im0.shape[:2])

        if pbar_cb is not None:
            pbar_cb()

    tracks_data = clear_empty_ids(tracker_annotations=tracks_data)

    return tracks_data


