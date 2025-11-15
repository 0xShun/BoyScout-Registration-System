"""
Forms for teacher registration and student management.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import formset_factory
from .models import User


class TeacherRegisterForm(UserCreationForm):
    """Form for teacher registration with .edu domain validation"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Update labels and placeholders
        self.fields['first_name'].widget.attrs.update({'placeholder': 'First Name'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Last Name'})
        self.fields['email'].widget.attrs.update({'placeholder': 'teacher@school.edu or teacher@university.edu.ph'})
        self.fields['email'].help_text = 'Must be a .edu email address'
        
        self.fields['phone_number'].label = "Phone Number"
        self.fields['phone_number'].widget.attrs.update({'placeholder': '+639XXXXXXXXX'})
        self.fields['phone_number'].required = False
        
        self.fields['password1'].label = "Password"
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a password'})
        self.fields['password1'].help_text = "Must be at least 8 characters."
        
        self.fields['password2'].label = "Confirm Password"
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm password'})
        self.fields['password2'].help_text = None
        
        # Make phone field permissive
        if 'phone_number' in self.fields:
            original_widget = self.fields['phone_number'].widget
            self.fields['phone_number'] = forms.CharField(required=False)
            self.fields['phone_number'].widget = original_widget
            self.fields['phone_number'].widget.attrs.update({'class': 'form-control', 'placeholder': '+639XXXXXXXXX'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('Email is required.')
        
        # Check for .edu domain
        if '.edu' not in email.lower():
            raise forms.ValidationError('Teacher registration requires a .edu email address (e.g., teacher@school.edu or teacher@university.edu.ph)')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(f'A user with email "{email}" already exists.')
        
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not phone:
            return phone
        phone_str = str(phone).strip()
        digits_only = ''.join(filter(str.isdigit, phone_str))
        if len(digits_only) == 11 and digits_only.startswith('09'):
            return f'+63{digits_only[1:]}'
        if len(digits_only) == 10 and digits_only.startswith('9'):
            return f'+63{digits_only}'
        if phone_str.startswith('+'):
            return phone_str
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Auto-generate username from first and last name
        base_username = f"{self.cleaned_data['first_name']}{self.cleaned_data['last_name']}".lower().replace(' ', '')
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username
        user.role = 'teacher'
        user.registration_status = 'inactive'  # Will be active after payment
        if commit:
            user.save()
        return user


class TeacherBulkStudentForm(forms.Form):
    """Form for registering students in bulk by teachers"""
    number_of_students = forms.IntegerField(
        min_value=1,
        max_value=50,
        required=True,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_number_of_students'}),
        label='Number of Students to Register',
        help_text='How many students will you register? (Max: 50)'
    )


class StudentForm(forms.Form):
    """Form for individual student information when registered by teacher"""
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
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@example.com'}),
        label='Email'
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+639XXXXXXXXX'}),
        label='Phone Number'
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date of Birth'
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Complete Address'}),
        label='Address'
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(f'A user with email "{email}" already exists.')
        return email


# Create formset for teacher bulk student registration (no password field - auto-generated)
StudentFormSet = formset_factory(StudentForm, extra=0, min_num=1, validate_min=True)


class StudentEditForm(forms.ModelForm):
    """Form for teachers to edit student profiles"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class StudentPasswordResetForm(forms.Form):
    """Form for teachers to reset student passwords"""
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        label='New Password',
        help_text='Must be at least 8 characters.'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        label='Confirm Password'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')
        
        if password and confirm and password != confirm:
            raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data
