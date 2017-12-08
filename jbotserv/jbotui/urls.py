"""jbotui URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.contrib import admin
from django.contrib.auth import views as auth_views
from jbotui import views
from jbotui import ajax


urlpatterns = [
    # General
    url(r'^login', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, name='logout'),

    url(r'^home', views.home),
    url(r'^settings', views.settings),

    # Devices
    url(r'^devices_list', views.devices_list),
    url(r'^devices_added', views.devices_added),
    url(r'^devices_add', views.devices_add),
    url(r'^devices', views.devices),
    url(r'^delete_device', ajax.delete_device),

    # Groups
    url(r'^groups_list', views.groups_list),
    url(r'^groups_added', views.groups_added),
    url(r'^groups_add', views.groups_add),
    url(r'^groups', views.groups),
    url(r'^delete_group', ajax.delete_group),

    # Images
    url(r'^images_list', views.images_list),
    url(r'^images_added', views.images_added),
    url(r'^images_upload', views.images_add),
    url(r'^images', views.images),
    url(r'^delete_image', ajax.delete_image),

    # Configuration Files

    # Tests
    url(r'^tests_list', views.tests_list),
    url(r'^tests_added', views.tests_added),
    url(r'^tests_upload', views.tests_add),
    url(r'^tests', views.tests),
    url(r'^delete_test', ajax.delete_test),

    # Execute
    url(r'^execute_request', ajax.execute_workflow),
    url(r'^execute', views.execute),
    url(r'^task_started', views.execution_started),

    # Tasks
    url(r'^tasks', views.tasks),

    # Results
    url(r'^results/(?P<task_id>(\w|[-]){1,50})', views.taskresultsdetail),
    url(r'^results$', views.taskresults),

    # New Workflow
    url(r'^new_workflow', views.new_workflow),

    url(r'^workflow', views.workflow),
    url(r'^get_running_tasks', ajax.get_running_tasks),
    url(r'^get_results', ajax.get_results),
    url(r'^running_tasks', views.running_tasks),
    url(r'^results', views.results),
    url(r'^run', views.run),
    url(r'^logs', views.logs),
    url(r'^saveworkflow', views.saveworkflow),
    url(r'^executeworkflow', views.executeworkflow),
    url(r'^jsnapuploadsuccess', views.jsnap_upload_success),
    url(r'^jsnapupload', views.jsnap_upload),
    url(r'^junosconfiguploadsuccess', views.junos_config_upload_success),
    url(r'^junosconfigupload', views.junos_config_upload),
    url(r'^junosimageuploadsuccess', views.junos_image_upload_success),
    url(r'^junosimageupload', views.junos_image_upload),
    
    url(r'^', views.home)
]
