from django import forms
from .models import Payment, PaymentQRCode, SystemConfiguration
from django.conf import settings
from accounts.models import User

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'receipt_image', 'reference_number']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'readonly': 'readonly'}),
            'receipt_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,application/pdf'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter payment reference number'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['amount'].label = "Payment Amount (₱)"
        self.fields['receipt_image'].label = "Payment Receipt"
        self.fields['receipt_image'].help_text = "Upload your payment receipt (JPG, PNG, or PDF, max 10MB)"
        self.fields['reference_number'].label = "Reference Number"
        self.fields['reference_number'].help_text = "Enter the payment reference number from your receipt"

    def clean_receipt_image(self):
        file = self.cleaned_data.get('receipt_image')
        if file:
            # Max 10MB
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File too large. Maximum is 10MB.')
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if hasattr(file, 'content_type') and file.content_type not in allowed_types:
                raise forms.ValidationError('Unsupported file type. Use JPG, PNG, or PDF.')
        return file

class PaymentQRCodeForm(forms.ModelForm):
    class Meta:
        model = PaymentQRCode
        fields = ['title', 'description', 'qr_code', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'qr_code': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].label = "QR Code Title"
        self.fields['description'].label = "Description"
        self.fields['qr_code'].label = "Payment QR Code Image"
        self.fields['qr_code'].help_text = "Upload a QR code image for general payments"
        self.fields['is_active'].label = "Active"
        self.fields['is_active'].help_text = "Only one QR code can be active at a time"


class TeacherPaymentForm(forms.ModelForm):
    """Form for teachers to submit payments on behalf of their students"""
    student = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Select Student",
        required=False
    )
    
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        label="Select Students (Bulk Payment)",
        required=False,
        help_text="Select multiple students to submit the same payment amount for each"
    )
    
    class Meta:
        model = Payment
        fields = ['student', 'students', 'amount', 'receipt_image', 'reference_number', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'receipt_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,application/pdf'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter payment reference number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, teacher, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active students managed by this teacher
        student_queryset = User.objects.filter(
            managed_by=teacher,
            registration_status='active'
        ).order_by('first_name', 'last_name')
        
        self.fields['student'].queryset = student_queryset
        self.fields['students'].queryset = student_queryset
        
        self.fields['amount'].label = "Payment Amount (₱)"
        self.fields['amount'].help_text = "This amount will be applied to each selected student"
        self.fields['receipt_image'].label = "Payment Receipt"
        self.fields['receipt_image'].help_text = "Upload payment receipt (JPG, PNG, or PDF, max 10MB)"
        self.fields['reference_number'].label = "Reference Number"
        self.fields['reference_number'].help_text = "Enter the payment reference number from your receipt"
        self.fields['notes'].label = "Notes (Optional)"
        self.fields['notes'].help_text = "Add any additional information about this payment"
        self.fields['notes'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        students = cleaned_data.get('students')
        
        # Ensure at least one selection method is used
        if not student and not students:
            raise forms.ValidationError('Please select at least one student (either from dropdown or checkboxes).')
        
        # Prevent using both methods
        if student and students:
            raise forms.ValidationError('Please use either single student dropdown OR multiple checkboxes, not both.')
        
        return cleaned_data

    def clean_receipt_image(self):
        file = self.cleaned_data.get('receipt_image')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File too large. Maximum is 10MB.')
            allowed = ['image/jpeg', 'image/png', 'application/pdf']
            if hasattr(file, 'content_type') and file.content_type not in allowed:
                raise forms.ValidationError('Unsupported file type. Use JPG, PNG, or PDF.')
        return file


class SystemConfigurationForm(forms.ModelForm):
    """Form for managing system-wide QR codes"""
    class Meta:
        model = SystemConfiguration
        fields = ['registration_fee']
        widgets = {
            'registration_fee': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '0',
                'step': '0.01',
                'placeholder': '500.00'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['registration_fee'].label = "Registration Fee Amount"
        self.fields['registration_fee'].help_text = "Set the registration fee amount (in Philippine Pesos)"
        self.fields['registration_fee'].required = True

    def clean_registration_fee(self):
        fee = self.cleaned_data.get('registration_fee')
        if fee and fee < 0:
            raise forms.ValidationError('Registration fee cannot be negative.')
        return fee
        return file
 