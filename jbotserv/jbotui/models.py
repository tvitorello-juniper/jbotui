# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.core.files.storage import FileSystemStorage

# Create your models here.

FSS = FileSystemStorage(location='/media/workflowfiles')

class Workflow(models.Model):
    name = models.CharField(max_length=255, primary_key=True, unique=True)
    data = models.FileField(upload_to='workflows')

class Procedure(models.Model):
    name = models.CharField(max_length=255, primary_key=True, unique=True)
    data = models.FileField(upload_to='procedures')

class Jsnap(models.Model):
    data = models.FileField(upload_to='tests')

class JunosImage(models.Model):
    data = models.FileField(upload_to='images')

class JunosConfig(models.Model):
    data = models.FileField(upload_to='configs')

class Device(models.Model):
    address = models.CharField(max_length=255, primary_key=True, unique=True)

class DeviceGroup(models.Model):
    name = models.CharField(max_length=255, primary_key=True, unique=True)
    members = models.ManyToManyField(Device)
