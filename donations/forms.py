# -*- coding: utf-8 -*-
from django import forms
from .models import DonationCampaign, Donation


class DonationCampaignForm(forms.ModelForm):
    """Form for creating and editing donation campaigns"""
    
    class Meta:
        model = DonationCampaign
        fields = [
            'title',
            'description',
            'banner_image',
            'qr_code_image',
            'external_payment_details',
            'goal_amount',
            'start_date',
            'end_date',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter campaign title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe the campaign and its purpose'
            }),
            'banner_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'qr_code_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'external_payment_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional payment instructions (optional)'
            }),
            'goal_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Target amount (leave blank for no goal)',
                'step': '0.01',
                'min': '0'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data


class DonationForm(forms.ModelForm):
    """Form for making a donation"""
    
    class Meta:
        model = Donation
        fields = ['amount', 'message', 'is_anonymous']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter donation amount',
                'step': '0.01',
                'min': '1',
                'required': True
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional message (visible to campaign organizers)'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount < 1:
            raise forms.ValidationError("Donation amount must be at least ₱1.00")
        return amount
