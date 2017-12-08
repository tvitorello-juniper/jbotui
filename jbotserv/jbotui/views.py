# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Standard Libraries
import json
from time import sleep
from datetime import datetime
from time import time
import kombu.five
from ast import literal_eval

# Django
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import permission_required

# Djago Models
from django.db import models
from jbotui.models import Workflow
from jbotui.models import Procedure
from jbotui.models import JunosImage
from jbotui.models import JunosConfig
from jbotui.models import Jsnap
from jbotui.models import Device
from jbotui.models import DeviceGroup

# Django Forms
from jbotui.forms import JunosImageForm
from jbotui.forms import JunosConfigForm
from jbotui.forms import JsnapForm
from jbotui.forms import DeviceForm
from jbotui.forms import DeviceGroupForm

# Celery
from django_celery_results.models import TaskResult
from jbotserv.celery import app as celery_app

# User-defined modules
from jbotui.jbotmanager import translator
from jbotui.jbotmanager.translator import TRError

# Create your views here.


#---------------------------------------------------------------------------------------------------
# Login
def login(request):
    return HttpResponse("Login")

def login_test(request):
    return HttpResponse('Login Test')

#---------------------------------------------------------------------------------------------------
# Home
def home(request):
    return render(request, 'home/home.html')

#---------------------------------------------------------------------------------------------------
# Settings
def settings(request):
    return HttpResponseRedirect("/admin/")

#---------------------------------------------------------------------------------------------------
# Device management
def devices(request):
    return render(request, "devices/option.html")

def devices_list(request):
    device_data = Device.objects.values('address')
    return render(request, "devices/list.html", {"devices": device_data})

def devices_add(request):
    if request.method == "POST":
        form = DeviceForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("devices_added")
    else:
        form = DeviceForm()
    return render(request, "devices/add.html", {'form': form})

def devices_added(request):
    return render(request, "devices/added.html")

#---------------------------------------------------------------------------------------------------
# Group management
def groups(request):
    return render(request, "groups/option.html")

def groups_list(request):
    group_data = DeviceGroup.objects.all()
    groups_members = {}
    for group in group_data:
        groups_members[group.name] = group.members.all().values('address')
    return render(request, "groups/list.html", {"groups": groups_members})

def groups_add(request):
    if request.method == "POST":
        form = DeviceGroupForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("groups_added")
    else:
        form = DeviceGroupForm()
    return render(request, "groups/add.html", {'form': form})

def groups_added(request):
    return render(request, "groups/added.html")

#---------------------------------------------------------------------------------------------------
# Image management
def images(request):
    return render(request, "images/option.html")

def images_list(request):
    image_data = JunosImage.objects.values('data')
    for image in image_data:
        image['data'] = str(image['data'])[7:]
    return render(request, "images/list.html", {"images": image_data})

def images_add(request):
    if request.method == "POST":
        form = JunosImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("images_added")
    else:
        form = JunosImageForm()
    return render(request, "images/add.html", {'form': form})

def images_added(request):
    return render(request, "images/added.html")

#---------------------------------------------------------------------------------------------------
# Test management
def tests(request):
    return render(request, "tests/option.html")

def tests_list(request):
    test_data = Jsnap.objects.values('data')
    for test in test_data:
        test['data'] = str(test['data'])[6:]
    return render(request, "tests/list.html", {"tests": test_data})

def tests_add(request):
    if request.method == "POST":
        form = JsnapForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("tests_added")
    else:
        form = JsnapForm()
    return render(request, "tests/add.html", {'form': form})

def tests_added(request):
    return render(request, "tests/added.html")

#---------------------------------------------------------------------------------------------------
# Execute Workflows
def execute(request):
    workflow_data = Workflow.objects.values("name")
    device_data = Device.objects.values('address')
    group_data = DeviceGroup.objects.all()
    groups_members = {}
    for group in group_data:
        groups_members[group.name] = group.members.all().values('address')
    return render(request, "execute/execute.html", {"devices": device_data, \
        "workflows": workflow_data, "groups": groups_members})

def execution_started(request):
    return render(request, 'execute/execution_started.html')

#---------------------------------------------------------------------------------------------------
# Running Tasks
def tasks(request):
    if request.method == "GET":
        celery_inspector = celery_app.control.inspect()
        tasks = {}
        for worker, worker_tasks in celery_inspector.active().iteritems():
            for task in worker_tasks:
                tasks[task['id']] = {}
                tasks[task['id']]['time'] = datetime.fromtimestamp(time() - \
                    (kombu.five.monotonic() - task['time_start'])).strftime('%H:%M %d/%m/%y %Z')
                args = task['args'][1:-1].split(",")
                workflow = args[0].strip().strip("'")
                target = args[1].strip().strip("'")
                tasks[task['id']]['workflow'] = workflow
                tasks[task['id']]['target'] = target
        return render(request, 'tasks/tasks.html', {'tasks': tasks})
    return HttpResponse("Unexpected request.")

#---------------------------------------------------------------------------------------------------
# Task Results
def taskresults(request):
    results = TaskResult.objects.all().values("date_done", "result", "task_id").order_by("-date_done")
    for result in results:
        result['result'] = literal_eval(result['result'])
    return render(request, 'taskresults/taskresults.html', {'results': results})

def taskresultsdetail(request, task_id):
    if request.method == "GET":
        try:
            task_entry = TaskResult.objects.get(task_id=task_id)
            task_info = {}
            task_info['task_id'] = task_entry.task_id
            task_info['task_date'] = task_entry.date_done
            task_results = literal_eval(task_entry.result)
            try:
                task_info['workflow'] = task_results['workflow']
                task_info['target'] = task_results['target']
                task_info['message'] = task_results['message']
                task_info['logs'] = task_results['logs']
            except KeyError:
                return HttpResponse("Task Information Key Error.")
            return render(request, "taskresults/taskresultsdetails.html", {'task_info': task_info})
        except ObjectDoesNotExist:
            return HttpResponse("Task does not exist.")
        except MultipleObjectsReturned:
            return HttpResponse("MultipleObjectsReturned.")
    else:
        return HttpResponse("Unexpected request.")

def new_workflow(request):
    return render(request, "workflow/workflow.html")









def index(request):
    return render(request, "index.html")



def workflow(request):
    return render(request, "workflow.html")

def saveworkflow(request):
    #-----------------------------------------------------------------------------------------------
    # Saves the received workflow to the database
    #-----------------------------------------------------------------------------------------------
    
    #-----------------------------------------------------------------------------------------------
    # Check request type for POST
    #-----------------------------------------------------------------------------------------------
    if request.method == 'POST':
        try:
            #---------------------------------------------------------------------------------------
            # Delete any entry with the same name
            #---------------------------------------------------------------------------------------
            Workflow.objects.filter(name=request.POST['workflowname']).delete()

            #---------------------------------------------------------------------------------------
            # Build the database entry and save
            #---------------------------------------------------------------------------------------
            data = {"flow":request.POST['workflowdata'], "set":request.POST['setdata']}
            workflow_file = ContentFile(data, name=request.POST['workflowname'])
            json.dump(data, workflow_file)
            new_workflow = Workflow(name=request.POST['workflowname'], data=workflow_file)
            new_workflow.save()

        #-------------------------------------------------------------------------------------------
        # Exception handlers
        #-------------------------------------------------------------------------------------------
        # Incomplete dataset
        except KeyError as err:
            return HttpResponse("Unable to save workflow. Missing argument: " + err.message)
        #-------------------------------------------------------------------------------------------
        # General handler to prevent server crash
        except Exception as err:
            return HttpResponse("Unexpected Error: " + err.message)

        #-------------------------------------------------------------------------------------------
        # Return confirmation message if no Exceptions where raised
        #-------------------------------------------------------------------------------------------
        return HttpResponse("Workflow saved successfully.")

    else:
        return HttpResponse("Unexpected request: " + str(request.method))

def run(request):
    return render(request, "run.html")

def executeworkflow(request):
    #-----------------------------------------------------------------------------------------------
    # Executes the procedure(s)
    #-----------------------------------------------------------------------------------------------

    #-----------------------------------------------------------------------------------------------
    # Check request type for POST
    #-----------------------------------------------------------------------------------------------
    if request.method == 'POST':
        try:
            #---------------------------------------------------------------------------------------
            # Get workflow name
            #---------------------------------------------------------------------------------------
            workflow_name = request.POST['workflow']

            #---------------------------------------------------------------------------------------
            # Delete any workflows with the same name
            #---------------------------------------------------------------------------------------
            Procedure.objects.filter(name=workflow_name).delete()

            #---------------------------------------------------------------------------------------
            # Get JSON workflow from database
            #---------------------------------------------------------------------------------------
            json_file = Workflow.objects.get(name=workflow_name)

            #---------------------------------------------------------------------------------------
            # Translate workflow
            #---------------------------------------------------------------------------------------
            yaml_file = translator.translate(json_file.name, json_file.data)

            #---------------------------------------------------------------------------------------
            # Save YAML workflow to database
            #---------------------------------------------------------------------------------------
            procedure = Procedure(name=workflow_name, data=yaml_file)
            procedure.save()

            #---------------------------------------------------------------------------------------
            # Execute workflow
            #---------------------------------------------------------------------------------------

            add.delay(4, 4)
            i = celery_app.control.inspect()
            sleep(1)
            print i.active()
            r = TaskResult.objects.all()
            for i in r:
                print i.result

            #---------------------------------------------------------------------------------------
            # Return the httpresponse
            #---------------------------------------------------------------------------------------
            return HttpResponse("Running workflow.")

        #-------------------------------------------------------------------------------------------
        # Exception handlers
        #-------------------------------------------------------------------------------------------
        # Workflow does not exist
        except ObjectDoesNotExist:
            return HttpResponse("Workflow does not exist.")
        #-------------------------------------------------------------------------------------------
        # Multiple workflows with the same name
        except MultipleObjectsReturned:
            return HttpResponse("Multiple workflows with the specified name.")
        # Incomplete dataset
        except KeyError as err:
            return HttpResponse("Unable to execute workflow(s). Missing argument: " + err.message)
        #-------------------------------------------------------------------------------------------
        # Translation Error
        except TRError as err:
            return HttpResponse("Workflow Error: " + err.message)
        #-------------------------------------------------------------------------------------------
        # General handler to prevent server crash
        except Exception as err:
            return HttpResponse("Unexpected Error: " + err.message)

    else:
        return HttpResponse("Unexpected request: " + str(request.method))

def logs(request):
    return render(request, "logs.html")



def junos_config_upload_success(request):
    return render(request, "junos_config_upload_success.html")

def junos_config_upload(request):
    if request.method == "POST":
        form = JunosConfigForm(request.POST, request.FILES)
        if form.is_valid():
            config_name = str(form.cleaned_data['data'])
            for config in JunosConfig.objects.filter(data="configs/" + config_name):
                config.delete()
            form.save()
            return HttpResponseRedirect("junosconfiguploadsuccess")
    else:
        form = JunosConfigForm()
    return render(request, 'junos_image_upload.html', {'form': form})

def junos_image_upload_success(request):
    return render(request, "junos_image_upload_success.html")

def junos_image_upload(request):
    if request.method == "POST":
        form = JunosImageForm(request.POST, request.FILES)
        if form.is_valid():
            image_name = str(form.cleaned_data['data'])
            for image in JunosImage.objects.filter(data="images/" + image_name):
                image.delete()
            form.save()
            return HttpResponseRedirect("junosimageuploadsuccess")
    else:
        form = JunosImageForm()
    return render(request, 'junos_image_upload.html', {'form': form})

def jsnap_upload_success(request):
    return render(request, "jsnap_upload_success.html")

def jsnap_upload(request):
    if request.method == "POST":
        form = JsnapForm(request.POST, request.FILES)
        if form.is_valid():
            jsnap_name = str(form.cleaned_data['data'])
            for jsnap in Jsnap.objects.filter(data="tests/" + jsnap_name):
                jsnap.delete()
            form.save()
            return HttpResponseRedirect("jsnapuploadsuccess")
    else:
        form = JsnapForm()
    return render(request, 'jsnap_upload.html', {'form': form})


def running_tasks(request):
    return render(request, 'running_tasks.html')

def results(request):
    return HttpResponse("")
