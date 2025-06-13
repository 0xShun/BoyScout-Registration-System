from django import forms
from .models import Payment
 
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payee_name', 'payee_email', 'amount', 'gcash_receipt_image']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

        if user:
            self.fields['payee_name'].initial = user.get_full_name()
            self.fields['payee_email'].initial = user.email 