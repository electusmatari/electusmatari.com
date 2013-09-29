from django import forms

from models import ReportCategory

class ReportCategoryForm(forms.ModelForm):
    class Meta:
        model = ReportCategory
        exclude = ('type',)
