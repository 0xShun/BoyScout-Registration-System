"""
Utility functions for generating payment reports (CSV format).
Combines data from Payment and EventPayment models.
"""
import csv
from io import StringIO
from django.http import HttpResponse
from django.utils import timezone
from payments.models import Payment
from events.models import EventPayment


def get_reference_number(payment_obj):
    """
    Extract reference number with priority: qr_ph_reference > paymongo_payment_id
    Works for both Payment and EventPayment models.
    """
    # Try qr_ph_reference first
    if hasattr(payment_obj, 'qr_ph_reference') and payment_obj.qr_ph_reference:
        return payment_obj.qr_ph_reference
    
    # Fall back to paymongo_payment_id
    if hasattr(payment_obj, 'paymongo_payment_id') and payment_obj.paymongo_payment_id:
        return payment_obj.paymongo_payment_id
    
    return 'N/A'


def get_payment_data_from_payment_model(payment):
    """
    Extract standardized payment data from Payment model (platform registration).
    Returns dict with: name, email, reference, amount, payment_type, date, method
    """
    return {
        'name': payment.user.get_full_name() if payment.user else 'N/A',
        'email': payment.user.email if payment.user else 'N/A',
        'reference': get_reference_number(payment),
        'amount': float(payment.amount),
        'payment_type': 'Platform Registration' if payment.payment_type == 'registration' else 'Other Payment',
        'date': payment.date.strftime('%Y-%m-%d %H:%M:%S') if payment.date else 'N/A',
        'method': payment.get_payment_method_display() if hasattr(payment, 'get_payment_method_display') else payment.payment_method,
    }


def get_payment_data_from_event_payment_model(event_payment):
    """
    Extract standardized payment data from EventPayment model (event-specific payments).
    Returns dict with: name, email, reference, amount, payment_type, date, method
    """
    event_title = event_payment.registration.event.title if event_payment.registration and event_payment.registration.event else 'Unknown Event'
    user = event_payment.registration.user if event_payment.registration else None
    
    return {
        'name': user.get_full_name() if user else 'N/A',
        'email': user.email if user else 'N/A',
        'reference': get_reference_number(event_payment),
        'amount': float(event_payment.amount),
        'payment_type': f'Event Payment: {event_title}',
        'date': event_payment.created_at.strftime('%Y-%m-%d %H:%M:%S') if event_payment.created_at else 'N/A',
        'method': event_payment.payment_method if event_payment.payment_method else 'N/A',
    }


def generate_payments_csv_response(payment_data_list, filename):
    """
    Generate CSV HttpResponse from a list of payment data dictionaries.
    
    Args:
        payment_data_list: List of dicts with keys: name, email, reference, amount, payment_type, date, method
        filename: The filename for the CSV download (e.g., 'payments_report_all_2024-11-23.csv')
    
    Returns:
        HttpResponse with CSV content
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Name', 'Email', 'Reference Number', 'Amount Paid', 'Payment Type', 'Payment Date', 'Payment Method'])
    
    # Write data rows
    for data in payment_data_list:
        writer.writerow([
            data['name'],
            data['email'],
            data['reference'],
            f"₱{data['amount']:.2f}",
            data['payment_type'],
            data['date'],
            data['method'],
        ])
    
    return response


def get_all_verified_payments_data():
    """
    Retrieve all verified payments from both Payment and EventPayment models.
    Returns a list of standardized payment data dictionaries sorted by date (newest first).
    """
    payment_data_list = []
    
    # Get all verified platform registration payments
    platform_payments = Payment.objects.filter(status='verified').select_related('user')
    for payment in platform_payments:
        payment_data_list.append(get_payment_data_from_payment_model(payment))
    
    # Get all verified event payments
    event_payments = EventPayment.objects.filter(status='verified').select_related(
        'registration__user', 'registration__event'
    )
    for event_payment in event_payments:
        payment_data_list.append(get_payment_data_from_event_payment_model(event_payment))
    
    # Sort by date (newest first)
    payment_data_list.sort(key=lambda x: x['date'], reverse=True)
    
    return payment_data_list


def get_event_verified_payments_data(event):
    """
    Retrieve all verified payments for a specific event.
    
    Args:
        event: Event model instance
    
    Returns:
        List of standardized payment data dictionaries sorted by date (newest first)
    """
    payment_data_list = []
    
    # Get all verified event payments for this specific event
    event_payments = EventPayment.objects.filter(
        status='verified',
        registration__event=event
    ).select_related('registration__user', 'registration__event')
    
    for event_payment in event_payments:
        payment_data_list.append(get_payment_data_from_event_payment_model(event_payment))
    
    # Sort by date (newest first)
    payment_data_list.sort(key=lambda x: x['date'], reverse=True)
    
    return payment_data_list
