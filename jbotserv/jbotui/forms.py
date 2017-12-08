from django import forms

from jbotui.models import JunosImage
from jbotui.models import JunosConfig
from jbotui.models import Jsnap
from jbotui.models import Device
from jbotui.models import DeviceGroup

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

#Operation Forms
class RebootForm(forms.Form):
    TARGETS = (
        ('master', 'Master'),
        ('backup', 'Backup'),
        ('single', 'Single'),
    )
    target = forms.ChoiceField(required=True, choices=TARGETS)

#Models Forms
class JunosImageForm(forms.ModelForm):
    class Meta:
        model = JunosImage
        fields = ["data"]
        # widgets = {
        #     'name': forms.TextInput(attrs={'class': 'junos_image_upload_name'}),
        # }
        labels = {
            "data": ""
        }

class JunosConfigForm(forms.ModelForm):
    class Meta:
        model = JunosConfig
        fields = ['data']
        labels = {
            "data": "File"
        }

class JsnapForm(forms.ModelForm):
    class Meta:
        model = Jsnap
        fields = ['data']
        labels = {
            "data": "File"
        }

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['address']
        labels = {
            "address": "Address",
        }

class DeviceGroupForm(forms.ModelForm):
    members = forms.CharField(widget=forms.Textarea )

    class Meta:
        model = DeviceGroup
        fields = ['name']
        labels = {
            'name': 'Group Name'
        }
        widgets = {
            'members': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super(DeviceGroupForm, self).__init__(*args, **kwargs)
        self.fields['members'].widget = forms.Textarea(attrs={
            'class': 'materialize-textarea',
            'placeholder': "Input members' addresses separated by commas"
            })

    def save(self, commit=True):

        instance = super(DeviceGroupForm, self).save(commit=False)

        if commit:
            instance.save()

        members_data = self.cleaned_data['members']
        members_data = members_data.split(",")
        for member in members_data:
            if member != "":
                try:
                    device = Device.objects.get(address=member.strip())
                    instance.members.add(device)
                except ObjectDoesNotExist:
                    print "Eita"
                except MultipleObjectsReturned:
                    print "Muitos eitas"

        if commit:
            instance.save()
