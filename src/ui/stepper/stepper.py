from typing import List
from supervisely.app.widgets import Widget


class StepperWidget(Widget):
    def __init__(self, steps: List[Widget], widget_id=None):
        self._steps = steps
        super().__init__(widget_id=widget_id, file_path=__file__)

    def get_json_data(self):
        return {}

    def get_json_state(self):
        return {}
