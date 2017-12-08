from __future__ import absolute_import, unicode_literals

from time import sleep
from datetime import datetime
import sys
import shlex
import cStringIO

# Celery
from celery import shared_task

# Process Control
import subprocess

# Models
from jbotui.models import Device
from jbotui.models import Workflow
from jbotui.models import Procedure

# Translator
from jbotui.jbotmanager.translator import translate, TRError


# Create your tasks here

# Execute procedure
@shared_task
def celery_execute_workflow(workflow_name, device_name, user, passwd):

    # get device and workflow
    device_entry = Device.objects.get(address=device_name)
    workflow_entry = Workflow.objects.get(name=workflow_name)

    # Create the result log
    result = {}
    result['workflow'] = workflow_name
    result['target'] = device_name
    result['message'] = ""
    result['logs'] = ""


    # Build the YAML procedure
    time = datetime.now().strftime("%Y-%m-%d  %H-%M-%S.%f")
    try:
        yaml_file = translate(workflow_name + "  " + time, workflow_entry.data)
    except TRError as err:
        result['message'] = "Workflow Error"
        result['logs'] = str(err)
        return result
    new_procedure = Procedure(yaml_file.name, yaml_file)
    new_procedure.save()


    # Build/get JBOT call parameters
    procedure = new_procedure.data.path
    target = device_entry.address

    cmd = "python -u jbot.py" + \
        " --procedure " + procedure + \
        " --user " + user + \
        " --passwd " + passwd + \
        " --targetA " + target + \
        " -c"

    cmd = shlex.split(cmd)

    # Try to execute command

    ssh_add_host_cmd = "expect ssh_add.exp " + target + " " + user + " " + passwd + " "
    ssh_add_host_cmd = shlex.split(ssh_add_host_cmd)
    try:
        sys.stdout.flush()
        ssh_process = subprocess.check_output(ssh_add_host_cmd, stderr=subprocess.STDOUT, universal_newlines=True)
    except Exception as err:
        result['message'] = "Execution Error"
        result['logs'] = str(err)
        return result

    try:
        sys.stdout.flush()
        process = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as err:
        result['message'] = "Execution Error"
        result['logs'] = str(err.output)
        return result
    except Exception as err:
        result['message'] = "Unknown Execution Error"
        result['logs'] = str(err)
        return result

    # Examine result
    result_string = cStringIO.StringIO(process)

    for line in result_string:
        if "PROCEDURE_ENDED" in line:
            if "finished successfully" in line:
                result['message'] = "Success"
                result['logs'] = process
                return result
            else:
                result['message'] = "Procedure Fail"
                result['logs'] = process
                return result
        if "TEST FAILED" in line:
            result['message'] = "SNAPSHOT VERIFICATION ERROR"
            result['logs'] = process
            return result
    
    # Assume a fail if the procedure does not explicitly ends successfully
    result['message'] = "Error"
    result['logs'] = process
    return result
