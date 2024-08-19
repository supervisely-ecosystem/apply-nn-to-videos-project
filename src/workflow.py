# This module contains the functions that are used to configure the input and output of the workflow for the current app.

import supervisely as sly

def workflow_input(api: sly.Api, project_id: int = None, session_id: int = None):
    if session_id is not None:
        api.app.workflow.add_input_task(int(session_id))
        sly.logger.debug(f"Workflow Input: Session ID - {session_id}")
    if project_id is not None:
        api.app.workflow.add_input_project(project_id)
        sly.logger.debug(f"Workflow Input: Project ID - {project_id}")


def workflow_output(api: sly.Api, project_id: int):
    api.app.workflow.add_output_project(project_id)    
    sly.logger.debug(f"Workflow Output: Project ID - {project_id}")
