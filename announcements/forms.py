from django import forms
from .models import Announcement

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'message', 'recipients']
        widgets = {
            'recipients': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        } 