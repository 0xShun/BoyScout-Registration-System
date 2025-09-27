from django import forms
from .models import Payment, PaymentQRCode
from django.conf import settings
 
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'gcash_receipt_image']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'gcash_receipt_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['amount'].label = "Payment Amount (₱)"
        self.fields['gcash_receipt_image'].label = "Payment Receipt Screenshot"
        self.fields['gcash_receipt_image'].help_text = "Upload a screenshot of your payment receipt"

    def clean_gcash_receipt_image(self):
        file = self.cleaned_data.get('gcash_receipt_image')
        if file:
            if file.size > getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024):
                raise forms.ValidationError('File too large. Maximum is 5MB.')
            allowed = set(getattr(settings, 'ALLOWED_IMAGE_TYPES', ['image/jpeg', 'image/png', 'image/gif']))
            if hasattr(file, 'content_type') and file.content_type not in allowed:
                raise forms.ValidationError('Unsupported file type. Use JPG/PNG/GIF.')
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