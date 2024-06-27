from supervisely.app.widgets import Widget, ProjectThumbnail
import src.sly_globals as g


class InputDataWidget(Widget):

    def __init__(self, project_info, widget_id=None):
        self._project_thumbnail = ProjectThumbnail(project_info)
        super().__init__(widget_id=widget_id, file_path=__file__)

    def get_json_data(self):
        return {}

    def get_json_state(self):
        return {}


input_data_widget = InputDataWidget(g.project_info)
