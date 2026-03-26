from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from ..models import Boat, Person, Crew


class CrewRegistrationForm(forms.Form):
    boat = forms.ModelChoiceField(
        queryset=Boat.objects.none(),
        label=_('Boat'),
        empty_label=_('— select a boat —'),
    )
    category = forms.ChoiceField(
        choices=[('', _('— select a category —'))] + Crew.CATEGORY_CHOICES,
        label=_('Category'),
    )
    helmsman = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        label=_('Helmsman'),
        empty_label=_('— select a person —'),
    )
    crew_member_1 = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        required=False,
        label=_('Crew member 1'),
        empty_label=_('—'),
    )
    crew_member_2 = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        required=False,
        label=_('Crew member 2'),
        empty_label=_('—'),
    )
    crew_member_3 = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        required=False,
        label=_('Crew member 3'),
        empty_label=_('—'),
    )
    crew_member_4 = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        required=False,
        label=_('Crew member 4'),
        empty_label=_('—'),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        visible_boats = Boat.objects.filter(
            Q(created_by=user) | Q(visible_to=user)
        ).distinct()
        visible_persons = Person.objects.filter(
            Q(regularparticipant__unit__entity__created_by=user) |
            Q(regularparticipant__unit__entity__editors=user) |
            Q(individualparticipant__entity__created_by=user) |
            Q(individualparticipant__entity__editors=user) |
            Q(organizer__entity__created_by=user) |
            Q(organizer__entity__editors=user) |
            Q(visible_to=user)
        ).distinct()
        self.fields['boat'].queryset = visible_boats
        for field in ['helmsman', 'crew_member_1', 'crew_member_2', 'crew_member_3', 'crew_member_4']:
            self.fields[field].queryset = visible_persons
        for fname in ['boat', 'helmsman', 'crew_member_1', 'crew_member_2', 'crew_member_3', 'crew_member_4']:
            self.fields[fname].widget.attrs.update({'class': 'form-select'})
        self.fields['category'].widget.attrs.update({'class': 'form-select'})

    def clean(self):
        cleaned_data = super().clean()
        participants = [
            cleaned_data.get('helmsman'),
            cleaned_data.get('crew_member_1'),
            cleaned_data.get('crew_member_2'),
            cleaned_data.get('crew_member_3'),
            cleaned_data.get('crew_member_4'),
        ]
        non_null = [p for p in participants if p is not None]
        if len(non_null) != len({p.pk for p in non_null}):
            raise forms.ValidationError(
                _('A participant cannot appear more than once in a crew.')
            )
        return cleaned_data
