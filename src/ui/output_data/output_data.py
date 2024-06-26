from supervisely.app.widgets import Widget, NotificationBox, SlyTqdm


apply_nn_to_video_project_progress = SlyTqdm(widget_id="apply_nn_to_video_project_progress")
current_video_progress = SlyTqdm(widget_id="current_video_progress")

apply_nn_notification_box = NotificationBox(
    title="Inference in Progress",
    description="Do not turn off the power of the Agent, it is processing data",
    widget_id="apply_nn_notification_box",
)


class OutputDataWidget(Widget):
    def __init__(self, widget_id=None):
        self.apply_nn_to_video_project_progress = apply_nn_to_video_project_progress
        self.current_video_progress = current_video_progress
        self.apply_nn_notification_box = apply_nn_notification_box
        super().__init__(widget_id=widget_id, file_path=__file__)

    def get_json_data(self):
        return {}

    def get_json_state(self):
        return {}


output_data_widget = OutputDataWidget()
