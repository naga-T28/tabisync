from django import forms
from django.forms import inlineformset_factory

from .models import MemoV2

class ContactForm(forms.Form):
    email = forms.EmailField(label="メールアドレス")
    name = forms.CharField(label="名前", max_length=100)
    subject = forms.CharField(label="お問い合わせタイトル", max_length=200)
    message = forms.CharField(label="お問い合わせ内容", widget=forms.Textarea)

class MemoV2Form(forms.ModelForm):
    class Meta:
        model = MemoV2
        fields = ["content"]

