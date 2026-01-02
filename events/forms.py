from django import forms
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Event, EventPhoto, EventRegistration, EventPayment

User = get_user_model()

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'time', 'location', 'banner', 'payment_amount']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control' }),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control' }),
            'title': forms.TextInput(attrs={'class': 'form-control' }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control' }),
            'payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Enter event fee (leave 0 for free events)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_amount'].help_text = "Set to 0 or leave blank for free events. Payment will be processed via PayMongo."

class EventPhotoForm(forms.ModelForm):
    class Meta:
        model = EventPhoto
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Enter a caption for the photo'}),
        }

class EventRegistrationForm(forms.ModelForm):
    PAYMENT_METHOD_CHOICES = [
        ('gcash', 'GCash'),
        ('paymaya', 'Maya (PayMaya)'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        required=False,
        initial='gcash',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Payment Method',
        help_text='Select your preferred e-wallet for payment'
    )
    
    class Meta:
        model = EventRegistration
        fields = ['rsvp']
        widgets = {
            'rsvp': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        # Show payment method only for paid events
        if self.event and self.event.has_payment_required:
            self.fields['payment_method'].required = True
            self.fields['payment_method'].help_text = f"Select payment method for ₱{self.event.payment_amount}"
        else:
            # Hide payment method for free events
            self.fields['payment_method'].widget = forms.HiddenInput()
            self.fields['payment_method'].required = False

class EventPaymentForm(forms.ModelForm):
    class Meta:
        model = EventPayment
        fields = ['amount', 'receipt_image', 'reference_number', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter payment amount',
                'readonly': 'readonly'
            }),
            'receipt_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,application/pdf'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter payment reference number'
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
        
        self.fields['reference_number'].label = "Reference Number"
        self.fields['reference_number'].help_text = "Enter the payment reference number from your receipt"
    
    def clean_receipt_image(self):
        file = self.cleaned_data.get('receipt_image')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File too large. Maximum is 10MB.')
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if hasattr(file, 'content_type') and file.content_type not in allowed_types:
                raise forms.ValidationError('Unsupported file type. Use JPG, PNG, or PDF.')
        return file

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
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        if teacher:
            # Only show students managed by this teacher
            self.fields['students'].queryset = User.objects.filter(
                managed_by=teacher,
                registration_status__in=['active', 'payment_verified']
            ).order_by('first_name', 'last_name')


from django.utils import timezone