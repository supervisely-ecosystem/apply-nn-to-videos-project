from supervisely.app.widgets import NotificationBox, SlyTqdm

preview_progress = SlyTqdm(widget_id='preview_progress')

here_will_be_preview_notification = NotificationBox(title='Here will be an Inference Preview', description='Click on the Preview button to generate video', widget_id='here_will_be_preview_notification')
