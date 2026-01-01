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
            'payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Enter event fee (leave 0 for free events)'}),
            'qr_code': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['qr_code'].label = "Event Payment QR Code"
        self.fields['qr_code'].help_text = "Upload QR-PH code for this event's payment (JPG or PNG, max 10MB). Leave blank for free events."
        self.fields['qr_code'].required = False
        self.fields['payment_amount'].help_text = "Set to 0 or leave blank for free events"
    
    def clean_qr_code(self):
        file = self.cleaned_data.get('qr_code')
        if file and hasattr(file, 'size'):
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File too large. Maximum is 10MB.')
            allowed_types = ['image/jpeg', 'image/png']
            if hasattr(file, 'content_type') and file.content_type not in allowed_types:
                raise forms.ValidationError('Unsupported file type. Use JPG or PNG.')
        return file

class EventPhotoForm(forms.ModelForm):
    class Meta:
        model = EventPhoto
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Enter a caption for the photo'}),
        }

class EventRegistrationForm(forms.ModelForm):
    reference_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter payment reference number'
        })
    )
    
    class Meta:
        model = EventRegistration
        fields = ['rsvp', 'receipt_image']
        widgets = {
            'rsvp': forms.Select(attrs={'class': 'form-select'}),
            'receipt_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,application/pdf'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        # Check if this is an existing registration (update) or new registration
        is_new_registration = not self.instance.pk
        
        if self.event and self.event.has_payment_required:
            # For new registrations, receipt and reference are required
            # For existing registrations, they're optional (allows updating RSVP without re-uploading)
            if is_new_registration:
                self.fields['receipt_image'].required = True
                self.fields['reference_number'].required = True
                self.fields['receipt_image'].help_text = f"Upload your payment receipt (JPG, PNG, or PDF, max 10MB). Event fee: ₱{self.event.payment_amount}"
                self.fields['reference_number'].help_text = "Enter the payment reference number from your receipt"
            else:
                self.fields['receipt_image'].required = False
                self.fields['reference_number'].required = False
                self.fields['receipt_image'].help_text = f"Upload additional payment receipt (optional). Event fee: ₱{self.event.payment_amount}"
                self.fields['reference_number'].help_text = "Enter the payment reference number (optional for additional payments)"
        else:
            self.fields['receipt_image'].required = False
            self.fields['receipt_image'].help_text = "Upload payment receipt (optional)"
            self.fields['reference_number'].required = False
    
    def clean_receipt_image(self):
        file = self.cleaned_data.get('receipt_image')
        if file and self.event and self.event.has_payment_required:
            # Max 10MB
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File too large. Maximum is 10MB.')
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if hasattr(file, 'content_type') and file.content_type not in allowed_types:
                raise forms.ValidationError('Unsupported file type. Use JPG, PNG, or PDF.')
        return file

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
    rsvp = forms.ChoiceField(
        choices=EventRegistration.RSVP_CHOICES,
        initial='yes',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='RSVP Status'
    )
    receipt_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,application/pdf'}),
        label='Payment Receipt (if applicable)',
        help_text='Upload one receipt for all selected students if event requires payment (JPG, PNG, or PDF, max 10MB)'
    )
    reference_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter payment reference number'}),
        label='Reference Number',
        help_text='Enter the payment reference number if uploading receipt'
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
    
    def clean_receipt_image(self):
        file = self.cleaned_data.get('receipt_image')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File too large. Maximum is 10MB.')
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if hasattr(file, 'content_type') and file.content_type not in allowed_types:
                raise forms.ValidationError('Unsupported file type. Use JPG, PNG, or PDF.')
        return file
    
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