from django import forms
from .models import Event, EventPhoto, EventRegistration

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'time', 'location', 'banner', 'qr_code', 'payment_amount']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'qr_code': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class EventPhotoForm(forms.ModelForm):
    class Meta:
        model = EventPhoto
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Enter a caption for the photo'}),
        }

class EventRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = ['rsvp', 'receipt_image']
        widgets = {
            'rsvp': forms.Select(attrs={'class': 'form-select'}),
            'receipt_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        if self.event and self.event.has_payment_required:
            self.fields['receipt_image'].required = True
            self.fields['receipt_image'].help_text = f"Please upload a screenshot of your payment receipt. Event fee: ₱{self.event.payment_amount}"
        else:
            self.fields['receipt_image'].required = False
            self.fields['receipt_image'].help_text = "Upload payment receipt (optional)" 