from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync

import src.sly_globals as g


def restart(data, state):
    data['done3'] = False


def generate_rows():
    rows = []
    g.available_classes_names = []
    obj_classes = g.model_meta.obj_classes
    for obj_class in obj_classes:
        rows.append(
            {
                'label': f'{obj_class.name}',
                'shapeType': f'{obj_class.geometry_type.geometry_name()}',
                'color': f'{"#%02x%02x%02x" % tuple(obj_class.color)}',
            }
        )

        g.available_classes_names.append(obj_class.name)
    return rows


def fill_table(table_rows):
    DataJson()['classesTable'] = table_rows
    run_sync(DataJson().synchronize_changes())


def selected_classes_event(state):
    g.selected_classes_list = []
    for idx, class_name in enumerate(g.available_classes_names):
        if state["selectedClasses"][idx] is True:
            g.selected_classes_list.append(class_name)
