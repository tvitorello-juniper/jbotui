"""Translator Module
Implements a translator from the JBOTUI JSON format to the JBOT YAML instruction set.
"""

import json
import ast
import yaml
import pprint

from django.core.files.base import ContentFile

from jbotui.jbotmanager.operation import Operation, OPError

class TRError(Exception):
    pass

def translate(workflow_name, workflow_file_path):
    """Generates the YAML procedure from the JSON file provided

    Args:
        workflow_name: the workflow name.
        workflow_file_path: the absolute path to the workflow file.

    Returns:
        yaml_workflow: a file-like object containing the workflow YAML representation.

    """
    #-----------------------------------------------------------------------------------------------
    # Load workflow file and data
    #-----------------------------------------------------------------------------------------------
    try:
        data = json.load(workflow_file_path)
        data_set = ast.literal_eval(data['set'])
        data_flow = ast.literal_eval(data['flow'])
    #-----------------------------------------------------------------------------------------------
    # Exception Handlers
    #-----------------------------------------------------------------------------------------------
    # File error
    except IOError:
        raise TRError("Unable to load specified workflow file.")
    #-----------------------------------------------------------------------------------------------
    # Dataset error
    except KeyError:
        raise TRError("Incomplete workflow information.")

    #-----------------------------------------------------------------------------------------------
    # Translation procedure begins here
    #-----------------------------------------------------------------------------------------------

    #-----------------------------------------------------------------------------------------------
    # Check and find 'Start' operation
    #-----------------------------------------------------------------------------------------------
    start_operation_id = _find_start(data_flow)

    #-----------------------------------------------------------------------------------------------
    # Create a file-like object and write base YAML
    #-----------------------------------------------------------------------------------------------
    yaml_workflow = ContentFile(\
"""
variables:
   targetA:
      type: target
      description: "Active target"

defaults: &defaults
  onError:  10000
  target: targetA

""", name=workflow_name + ".yaml")
    yaml_workflow.open()
    yaml_workflow.seek(0, 2) # Go to end of file

    #-----------------------------------------------------------------------------------------------
    # Reparse links into a simpler data structure
    #-----------------------------------------------------------------------------------------------
    next_links = {}
    for link_id, link in data_flow['links'].iteritems():
        if link['fromConnector'] == "output_1":
            next_links[str(link['fromOperator'])] = str(link['toOperator'])

    #-----------------------------------------------------------------------------------------------
    # Iterate through procedures until the next operations does not exist.
    #-----------------------------------------------------------------------------------------------
    current_operation = start_operation_id
    current_step = 0
    while True:
        #-------------------------------------------------------------------------------------------
        # Get operation title and entry in the settings dictionary
        try:
            title = data_flow['operators'][current_operation]['properties']['title']
        except KeyError:
            raise TRError("Incomplete operation settings in: " + current_operation)
        try:
            setti = data_set[current_operation]
        except KeyError:
            setti = {}
        #-------------------------------------------------------------------------------------------
        # Construct the operation object, retrieve string representation and write to file
        try:
            op = Operation(str(current_step), title, setti)
            yaml_rep = op.get_procedure()
            yaml_workflow.write(yaml_rep)
        except TRError:
            raise
        except OPError as err:
            raise TRError(err.message)
        except Exception as err:
            raise TRError("Unknow error during translation: " + err.message)

        #-------------------------------------------------------------------------------------------
        # Break if there is no next operation
        if len(data_flow['operators'][current_operation]['properties']['outputs']) == 0:
            break

        #-------------------------------------------------------------------------------------------
        # Get next operation
        try:
            current_operation = next_links[current_operation]
            current_step += 10
        #-------------------------------------------------------------------------------------------
        # Handle no next link
        except KeyError:
            raise TRError('No specified next link in the operation: "' + title + '".')

    #-----------------------------------------------------------------------------------------------
    # Add the end_failure to the end of the file
    #-----------------------------------------------------------------------------------------------
    yaml_workflow.write("""
10000:
   end_failure:

""")
    #-----------------------------------------------------------------------------------------------
    # Close output file and return it
    #-----------------------------------------------------------------------------------------------
    yaml_workflow.seek(0)
    yaml_workflow.close()
    return yaml_workflow

def _find_start(data_flow):
    """Locates the start block in the workflow procedure. Also verifies it exists and is unique.

    Args:
        data_flow: Dictionary containing the workflow structure.

    Returns:
        start: The operation ID of the unique "Start" operation.

    """
    start = None
    for operator, operator_data in data_flow['operators'].iteritems():
        if operator_data['properties']['title'] == 'Start':
            if start is None:
                start = operator
            else:
                raise TRError('Multiple "Start" blocks defeined in the workflow procedure')
    if start is None:
        raise TRError('No "Start" block defined in the workflow procedure')
    else:
        return start
