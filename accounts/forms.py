from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from .models import User, Group
from django.conf import settings

# The current form doesn't have a csrf token yet.
#


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
                    # Check registration payment status for more specific message
                    reg_payment = user.registration_payments.filter(status='verified').exists()
                    if not reg_payment:
                        raise forms.ValidationError("Your registration payment is not yet verified. Please wait for admin approval.")
                    else:
                        raise forms.ValidationError("This account is not active. Please verify your email first.")
            except User.DoesNotExist:
                # Don't raise validation error here - let Django's authentication handle it
                pass
        
        return cleaned_data

class UserRegisterForm(UserCreationForm):
    rank = forms.ChoiceField(
        choices=[('scout', 'Scout'), ('teacher', 'Teacher')],
        initial='scout',
        label='Register as',
        help_text='Choose whether you are registering as a Scout or Teacher'
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'address', 'rank']
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

        self.fields['rank'].widget.attrs.update({'class': 'form-select'})
        
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
        if username and User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username


class AdminCreateTeacherForm(UserCreationForm):
    """Form for admins to create teacher accounts directly"""
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

        # Email is required
        self.fields['email'].required = True
        self.fields['email'].help_text = "Teacher will receive login credentials via email"
        
        # Username is required
        self.fields['username'].required = True
        self.fields['username'].help_text = "Unique username for login"
        
        # Make some fields optional
        self.fields['phone_number'].required = False
        self.fields['date_of_birth'].required = False
        self.fields['address'].required = False
        
        # Password fields
        self.fields['password1'].label = "Password"
        self.fields['password1'].help_text = "Create a password for the teacher (minimum 8 characters)"
        self.fields['password2'].label = "Confirm Password"
        self.fields['password2'].help_text = None

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rank = 'teacher'
        user.is_active = True
        user.registration_status = 'pending_payment'  # Teachers need to pay registration fee
        user.registration_amount_required = 500  # Standard registration fee
        
        if commit:
            user.save()
        return user

    def clean(self):
        cleaned_data = super().clean()
        # Validate receipt file size and type if provided
        receipt = self.files.get('registration_receipt')
        if receipt:
            if receipt.size > getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024):
                self.add_error('registration_receipt', 'File too large. Maximum is 5MB.')
            allowed = set(getattr(settings, 'ALLOWED_IMAGE_TYPES', ['image/jpeg', 'image/png', 'image/gif']))
            if hasattr(receipt, 'content_type') and receipt.content_type not in allowed:
                self.add_error('registration_receipt', 'Unsupported file type. Use JPG/PNG/GIF.')
        return cleaned_data

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

class TeacherCreateStudentForm(UserCreationForm):
    """Form for teachers to create student accounts"""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

        # Make username auto-generated hint
        self.fields['username'].help_text = "Leave blank to auto-generate from first and last name"
        self.fields['username'].required = False
        
        # Email is required
        self.fields['email'].required = True
        self.fields['email'].help_text = "Student will receive login credentials via email"
        
        # Make some fields optional
        self.fields['phone_number'].required = False
        self.fields['date_of_birth'].required = False
        self.fields['address'].required = False
        
        # Password fields
        self.fields['password1'].label = "Password"
        self.fields['password1'].help_text = "Create a password for the student (minimum 8 characters)"
        self.fields['password2'].label = "Confirm Password"
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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rank = 'scout'  # Students are scouts by default
        user.managed_by = self.teacher
        user.is_active = True
        user.registration_status = 'pending_payment'  # Teachers must pay for students via PayMongo
        
        # Auto-generate username if not provided
        if not user.username:
            from django.utils.text import slugify
            base_username = slugify(f"{user.first_name}_{user.last_name}")
            unique_username = base_username
            counter = 1
            while User.objects.filter(username=unique_username).exists():
                unique_username = f"{base_username}_{counter:03d}"
                counter += 1
            user.username = unique_username
        
        if commit:
            user.save()
        return user

class TeacherEditStudentForm(forms.ModelForm):
    """Form for teachers to edit student accounts they manage"""
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'username',
            'date_of_birth', 'phone_number', 'address', 
            'emergency_contact', 'emergency_phone',
            'medical_conditions', 'allergies'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 3}),
            'allergies': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

        

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username