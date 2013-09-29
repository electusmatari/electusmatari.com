from django import forms

CORPORATION_CHOICES = [
    (None, 'Myself only'),
    ('Gradient', 'Gradient Recruiters'),
    ('Lutinari Syndicate', 'Lutinari Syndicate Recruiters'),
]

class APIKeyForm(forms.Form):
    userid = forms.CharField()
    apikey = forms.CharField()
    visibility = forms.ChoiceField(choices=CORPORATION_CHOICES,
                                   required=False)
