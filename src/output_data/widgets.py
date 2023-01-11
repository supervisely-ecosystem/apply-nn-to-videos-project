from supervisely.app.widgets import NotificationBox, SlyTqdm

apply_nn_to_video_project_progress = SlyTqdm()
current_video_progress = SlyTqdm()

apply_nn_notification_box = NotificationBox(title='Inference in Progress', description='Do not turn off the power of the Agent, it is processing data', widget_id='apply_nn_notification_box')
