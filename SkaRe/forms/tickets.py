from django import forms
from django.utils.translation import gettext_lazy as _


class BulkTicketCreateForm(forms.Form):
    p550_reserves = forms.IntegerField(
        min_value=0, initial=0, required=True,
        label=_('P550 reserve tickets'),
        help_text=_('Extra P550 tickets beyond registered P550 boats'),
    )
    sail_reserves = forms.IntegerField(
        min_value=0, initial=0, required=True,
        label=_('Sailboat reserve tickets'),
        help_text=_('Extra sailboat tickets beyond registered sailboats'),
    )
    other_reserves = forms.IntegerField(
        min_value=0, initial=0, required=True,
        label=_('Other boat reserve tickets'),
        help_text=_('Extra other-boat tickets beyond registered other boats'),
    )
    spare_count = forms.IntegerField(
        min_value=0, initial=0, required=True,
        label=_('Spare tickets'),
        help_text=_('Spare tickets not assigned to any boat'),
    )
