from django import forms
from django.forms import inlineformset_factory

from .models import MemoV2

class MemoV2Form(forms.ModelForm):
    class Meta:
        model = MemoV2
        fields = ["content"]

