from src.ui.stepper.stepper import StepperWidget
from src.ui.input_data.input_data import input_data_widget
from src.ui.connect_to_model.connect_to_model import connect_to_model_widget
from src.ui.choose_classes.choose_classes import choose_classes_widget
from src.ui.parameters.parameters import parameters_widget
from src.ui.output_data.output_data import output_data_widget


layout = StepperWidget(
    [
        input_data_widget,
        connect_to_model_widget,
        choose_classes_widget,
        parameters_widget,
        output_data_widget,
    ]
)
