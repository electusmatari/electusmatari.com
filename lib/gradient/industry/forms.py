from django import forms

from gradient.industry.models import WantedMarketOrder, StockLevel
from gradient.industry.models import BlueprintOriginal
from gradient.dbutils import get_itemname, get_itemid
from gradient.dbutils import get_typename, get_typeid

class StationField(forms.CharField):
    def clean(self, data):
        data = super(StationField, self).clean(data)
        data = data.strip()
        stationid = get_itemid(data)
        if stationid is None:
            raise forms.ValidationError('Station not found')
        return get_itemname(stationid)

    def widget_attrs(self, widget):
        return {'class': 'stationinput'}

class InvTypeField(forms.CharField):
    def clean(self, data):
        data = super(InvTypeField, self).clean(data)
        data = data.strip()
        typeid = get_typeid(data)
        if typeid is None:
            raise forms.ValidationError('Type name not found')
        return get_typename(typeid)

    def widget_attrs(self, widget):
        return {'class': 'typeinput'}

class BlueprintTypeField(forms.CharField):
    def clean(self, data):
        data = super(BlueprintTypeField, self).clean(data)
        data = data.strip()
        typeid = get_typeid(data)
        if typeid is None:
            raise forms.ValidationError('Blueprint name not found')
        return get_typename(typeid)

    def widget_attrs(self, widget):
        return {'class': 'bpinput'}

class WantedMarketOrderForm(forms.ModelForm):
    stationname = StationField()
    typename = InvTypeField()

    class Meta:
        model = WantedMarketOrder
        fields = ('stationname', 'typename', 'forcorp',
                  'ordertype', 'quantity', 'comment')

class StockLevelForm(forms.ModelForm):
    stationname = StationField()
    typename = InvTypeField()

    class Meta:
        model = StockLevel
        fields = ('stationname', 'typename', 'low', 'high', 'comment')

class BlueprintOriginalForm(forms.ModelForm):
    typename = BlueprintTypeField()

    class Meta:
        model = BlueprintOriginal
        fields = ['typename', 'me', 'pe']

