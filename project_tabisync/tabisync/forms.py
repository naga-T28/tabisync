from django import forms
from django.forms import inlineformset_factory
from .models import Shiori, Schedule

class ShioriForm(forms.ModelForm):
    class Meta:
        model = Shiori
        fields = ['title', 'subtitle', 'summary_title', 'summary_detail']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'summary_title': forms.TextInput(attrs={'class': 'form-control'}),
            'summary_detail': forms.Textarea(attrs={'class': 'form-control', 'rows':4}),
        }

class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['date', 'time', 'detail']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'detail': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

ScheduleFormSet = inlineformset_factory(
    Shiori, Schedule, form=ScheduleForm,
    extra=1, can_delete=True
)
