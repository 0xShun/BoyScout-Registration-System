from django import forms
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Event, EventPhoto, EventRegistration, EventPayment

User = get_user_model()

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'time', 'location', 'banner', 'qr_code', 'payment_amount']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control' }),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control' }),
            'title': forms.TextInput(attrs={'class': 'form-control' }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control' }),
            'payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'qr_code': forms.ClearableFileInput(attrs={'class': 'form-control' }),
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

class TeacherBulkEventRegistrationForm(forms.Form):
    """Form for teachers to register multiple students for an event"""
    event = forms.ModelChoiceField(
        queryset=Event.objects.filter(date__gte=timezone.now()).order_by('date', 'time'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Event'
    )
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Select Students to Register'
    )
    rsvp = forms.ChoiceField(
        choices=EventRegistration.RSVP_CHOICES,
        initial='yes',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='RSVP Status'
    )
    receipt_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label='Payment Receipt (if applicable)',
        help_text='Upload one receipt for all students if payment is required'
    )
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        if teacher:
            # Only show students managed by this teacher
            self.fields['students'].queryset = User.objects.filter(
                managed_by=teacher,
                registration_status__in=['active', 'payment_verified']
            ).order_by('last_name', 'first_name')
    
    def clean(self):
        cleaned_data = super().clean()
        event = cleaned_data.get('event')
        students = cleaned_data.get('students')
        receipt_image = cleaned_data.get('receipt_image')
        
        if event and event.has_payment_required and students and not receipt_image:
            raise forms.ValidationError(
                f'This event requires payment (₱{event.payment_amount} per student). Please upload a payment receipt.'
            )
        
        return cleaned_data


from django.utils import timezone