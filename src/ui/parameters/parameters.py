from supervisely.app.widgets import Widget, NotificationBox, SlyTqdm

preview_progress = SlyTqdm(widget_id="preview_progress")

here_will_be_preview_notification = NotificationBox(
    title="Here will be an Inference Preview",
    description="Click on the Preview button to generate video",
    widget_id="here_will_be_preview_notification",
)


class ParametersWidget(Widget):
    def __init__(self, widget_id=None):
        self.preview_progress = preview_progress
        self.here_will_be_preview_notification = here_will_be_preview_notification
        super().__init__(widget_id=widget_id, file_path=__file__)

    def get_json_data(self):
        return {}

    def get_json_state(self):
        return {}


parameters_widget = ParametersWidget()
