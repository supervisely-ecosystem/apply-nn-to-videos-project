from supervisely.app import DataJson
from supervisely.app.fastapi import run_sync


def restart(data, state):
    data['done3'] = False


def generate_rows():
    rows = []
    obj_classes = g.model_meta.obj_classes
    for obj_class in obj_classes:


        rows.append(
            {
                'label': f'{obj_class.name}',
                'shapeType': f'{obj_class.geometry_type.geometry_name()}',
                'color': f'{"#%02x%02x%02x" % tuple(obj_class.color)}',
            }
        )
    return rows


def fill_table(table_rows):
    DataJson()['classesTable'] = table_rows
    run_sync(DataJson().synchronize_changes())

