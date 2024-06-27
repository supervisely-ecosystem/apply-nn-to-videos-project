from supervisely.app.widgets import Widget, ElementButton


select_all_classes_button = ElementButton(
    text='<i class="zmdi zmdi-check-all"></i> SELECT ALL',
    button_type="text",
    button_size="mini",
    plain=True,
    widget_id="select_all_classes_button",
)
deselect_all_classes_button = ElementButton(
    text='<i class="zmdi zmdi-square-o"></i> DESELECT ALL',
    button_type="text",
    button_size="mini",
    plain=True,
    widget_id="deselect_all_classes_button",
)


class ChooseClassesWidget(Widget):
    def __init__(self, widget_id=None):
        self.select_all_classes_button = select_all_classes_button
        self.deselect_all_classes_button = deselect_all_classes_button
        super().__init__(widget_id=widget_id, file_path=__file__)

    def get_json_data(self):
        return {}

    def get_json_state(self):
        return {}


choose_classes_widget = ChooseClassesWidget()
