from supervisely.app.widgets import NotificationBox, SlyTqdm

apply_nn_to_video_project_progress = SlyTqdm()
current_video_progress = SlyTqdm()

apply_nn_notification_box = NotificationBox(title='Labeling in Progress', description='do not turn off the power of the agent, it is processing data')
