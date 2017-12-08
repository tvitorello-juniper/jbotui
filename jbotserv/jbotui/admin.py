# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from jbotui.models import Device
from jbotui.models import DeviceGroup
from jbotui.models import JunosImage
from jbotui.models import Procedure
from jbotui.models import Jsnap

# Register your models here.
admin.site.register(Device)
admin.site.register(DeviceGroup)
admin.site.register(JunosImage)
admin.site.register(Procedure)
admin.site.register(Jsnap)
