from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import User, Group, BatchRegistration
from django.conf import settings
from django.forms import formset_factory

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
                    raise forms.ValidationError(
                        "Your account has been deactivated by the administrator. "
                        "Please contact support for assistance."
                    )
            except User.DoesNotExist:
                # Don't raise validation error here - let Django's authentication handle it
                pass
        
        return cleaned_data

class UserRegisterForm(UserCreationForm):
    # Amount is now fixed and set by admin, not editable by user
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'address']
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

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

class UserEditForm(forms.ModelForm):
    profile_image = forms.ImageField(required=False, label="Profile Picture")
    class Meta:
        model = User
        fields = [
            'profile_image', 'username', 'email', 'first_name', 'last_name', 'rank',
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

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        date_of_birth = cleaned_data.get('date_of_birth')
        if first_name and last_name and date_of_birth:
            qs = User.objects.filter(first_name__iexact=first_name.strip(), last_name__iexact=last_name.strip(), date_of_birth=date_of_birth)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Another member with the same name and date of birth already exists. Please check your information or contact admin.')
        return cleaned_data

class RoleManagementForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all(), label="Select User")
    rank = forms.ChoiceField(choices=User.RANK_CHOICES, label="New Rank") 

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BatchRegistrarForm(forms.Form):
    """Form for teacher/registrar information in batch registration"""
    
    # Fields for batch registration
    registrar_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
        label='Teacher/Registrar Name'
    )
    registrar_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your email address'}),
        label='Teacher/Registrar Email'
    )
    registrar_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+639XXXXXXXXX'}),
        label='Teacher/Registrar Phone'
    )
    number_of_students = forms.IntegerField(
        min_value=1,
        max_value=50,
        required=True,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_number_of_students'}),
        label='Number of Students to Register',
        help_text='How many students will you register? (Max: 50)'
    )


class BatchStudentForm(forms.Form):
    """Form for individual student information in batch registration"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        label='Username'
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
        label='First Name'
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
        label='Last Name'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        label='Email'
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+639XXXXXXXXX'}),
        label='Phone Number'
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date of Birth'
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Complete Address'}),
        label='Address'
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password (min 8 characters)'}),
        label='Password',
        help_text='Must be at least 8 characters.'
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(f'A user with email "{email}" already exists.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(f'Username "{username}" is already taken.')
        return username


# Create formset for batch student registration
BatchStudentFormSet = formset_factory(BatchStudentForm, extra=0, min_num=1, validate_min=True)