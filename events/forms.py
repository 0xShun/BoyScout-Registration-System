from django import forms
from .models import Event, EventPhoto, EventRegistration, EventPayment, CertificateTemplate

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'time', 'location', 'banner', 'payment_amount']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_amount': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01', 
                'min': '0',
                'placeholder': 'Leave blank for free events'
            }),
            'banner': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'payment_amount': 'Enter the event fee. Leave blank or set to 0 for free events. Payments will be processed via QR PH.',
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

class EventPaymentForm(forms.ModelForm):
    class Meta:
        model = EventPayment
        fields = ['amount', 'receipt_image', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter payment amount'
            }),
            'receipt_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes about this payment'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.registration = kwargs.pop('registration', None)
        super().__init__(*args, **kwargs)
        
        if self.registration:
            remaining = self.registration.amount_remaining
            if remaining > 0:
                self.fields['amount'].help_text = f"Remaining amount to pay: ₱{remaining}"
                self.fields['amount'].widget.attrs['max'] = str(remaining)
            else:
                self.fields['amount'].help_text = "Event is fully paid" 


class CertificateTemplateForm(forms.ModelForm):
    """Form for uploading and configuring certificate templates."""

    class Meta:
        model = CertificateTemplate
        fields = [
            'template_image',
            'certificate_name',
            'name_x',
            'name_y',
            'name_font_size',
            'name_color',
            'event_x',
            'event_y',
            'event_font_size',
            'event_color',
            'date_x',
            'date_y',
            'date_font_size',
            'date_color',
            'certificate_number_x',
            'certificate_number_y',
            'certificate_number_font_size',
            'certificate_number_color',
            'is_active',
        ]
        widgets = {
            'template_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'help_text': 'Upload PNG or JPG. Recommended size: 1200x800 pixels or larger'
            }),
            'certificate_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Certificate of Participation'
            }),
            # Scout Name Configuration
            'name_x': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
            }),
            'name_y': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
            }),
            'name_font_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'max': '120',
            }),
            'name_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'title': 'Hex color (e.g., #000000)'
            }),
            # Event Name Configuration
            'event_x': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'event_y': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'event_font_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'max': '120',
            }),
            'event_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
            }),
            # Date Configuration
            'date_x': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'date_y': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'date_font_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'max': '120',
            }),
            'date_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
            }),
            # Certificate Number Configuration
            'certificate_number_x': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'required': False,
            }),
            'certificate_number_y': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'required': False,
            }),
            'certificate_number_font_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '8',
                'max': '120',
            }),
            'certificate_number_color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        } 