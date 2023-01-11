from supervisely.app.widgets import NotificationBox, ElementButton

select_all_classes_button = ElementButton(text='<i class="zmdi zmdi-check-all"></i> SELECT ALL', button_type='text', button_size='mini', plain=True, widget_id='select_all_classes_button')
deselect_all_classes_button = ElementButton(text='<i class="zmdi zmdi-square-o"></i> DESELECT ALL', button_type='text', button_size='mini', plain=True, widget_id='deselect_all_classes_button')

