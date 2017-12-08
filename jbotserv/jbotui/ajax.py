# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Standard Libraries
import json
from time import sleep

# Django
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required

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

# Django Tasks
from jbotui.tasks import celery_execute_workflow

# Celery
from django_celery_results.models import TaskResult
from jbotserv.celery import app as celery_app

# User-defined modules
from jbotui.jbotmanager import translator
from jbotui.jbotmanager.translator import TRError

def get_running_tasks(request):
    if request.method == "GET":
        celery_inspector = celery_app.control.inspect()
        active_tasks = []
        for worker, worker_tasks in celery_inspector.active().iteritems():
            for task in worker_tasks:
                active_tasks.append(task)
        return HttpResponse(json.dumps(active_tasks))
    return HttpResponse("Unexpected request.")

def get_results(request):
    if request.method == "GET":
        for result in TaskResult.objects.all():
            return HttpResponse("")
    return HttpResponse("Unexpected request.")

def delete_device(request):
    if request.method == "POST":
        Device.objects.get(address=request.POST.get("address")).delete()
        return HttpResponse("Device deleted.")
    return HttpResponse("Unexpected request.")

def delete_image(request):
    if request.method == "POST":
        quer = "images/" + request.POST.get("name")
        JunosImage.objects.get(data=quer).delete()
        return HttpResponse("Image deleted.")
    return HttpResponse("Unexpected request.")

def delete_test(request):
    if request.method == "POST":
        quer = "tests/" + request.POST.get("test_name")
        Jsnap.objects.get(data=quer).delete()
        return HttpResponse("Test deleted.")
    return HttpResponse("Unexpected request.")

def delete_group(request):
    if request.method == "POST":
        DeviceGroup.objects.get(name=request.POST.get("name")).delete()
        return HttpResponse("Group deleted.")
    return HttpResponse("Unexpected request.")

def execute_workflow(request):
    if request.method == "POST":
        workflow = request.POST['workflow']
        login = request.POST['login']
        passwd = request.POST['passwd']
        targets = set()
        if request.POST['execute_on'] == "groups":
            groups = request.POST.getlist('groups[]')
            for group in groups:
                devicegroup = DeviceGroup.objects.get(name=group)
                for member in devicegroup.members.all():
                    targets.add(member.address)
            print targets
        elif request.POST['execute_on'] == "devices":
            devices = request.POST.getlist('devices[]')
            for device in devices:
                targets.add(device)
        for target in targets:
            celery_execute_workflow.delay(workflow, target, login, passwd)
        return HttpResponse("Received Execute request")
    return HttpResponse("Unnexpected request.")
