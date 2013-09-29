from django import forms

class APIKeyForm(forms.Form):
    keyid = forms.CharField(max_length=8)
    vcode = forms.CharField(max_length=64)
