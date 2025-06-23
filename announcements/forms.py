from django import forms
from .models import Announcement

class AnnouncementForm(forms.ModelForm):
    send_email = forms.BooleanField(required=False, label="Send Email Notification")
    send_sms = forms.BooleanField(required=False, label="Send SMS Notification (Simulation)")

    class Meta:
        model = Announcement
        fields = ['title', 'message', 'recipients', 'send_email', 'send_sms']
        widgets = {
            'recipients': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        } 