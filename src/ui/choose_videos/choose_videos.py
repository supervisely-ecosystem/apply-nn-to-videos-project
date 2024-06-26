from supervisely.app.widgets import Widget


class ChooseVideosWidget(Widget):
    def __init__(self, widget_id=None):
        super().__init__(widget_id=widget_id, file_path=__file__)

    def get_json_data(self):
        return {}

    def get_json_state(self):
        return {}
