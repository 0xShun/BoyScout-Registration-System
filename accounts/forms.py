from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import User

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Email',
                'aria-label': 'Email',
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Password',
                'aria-label': 'Password',
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = ""
        self.fields['password'].label = ""

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            try:
                user = User.objects.get(email=username)
                if not user.is_active:
                    raise forms.ValidationError("This account is not active. Please verify your email first.")
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid email or password.")
        
        return cleaned_data

class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'date_of_birth', 'phone_number', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

        self.fields['email'].widget.attrs.update({'placeholder': 'Enter your email'})
        self.fields['password1'].label = "Password"
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a password'})
        self.fields['password2'].label = "Confirm password"
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm password'})

        self.fields['date_of_birth'].label = "Date of Birth"
        self.fields['phone_number'].label = "Phone Number"
        self.fields['phone_number'].widget.attrs.update({'placeholder': 'Enter your phone number'})

        self.fields['address'].label = "Address"
        self.fields['address'].widget.attrs.update({'placeholder': 'Enter your address'})

        self.fields['password1'].help_text = "Must be at least 8 characters."
        self.fields['password2'].help_text = None


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'rank',
            'date_of_birth', 'phone_number', 'address', 'emergency_contact',
            'emergency_phone', 'medical_conditions', 'allergies'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 3}),
            'allergies': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'}) 