# Batch Registration Feature - Complete Guide

## Overview
The Batch Registration feature allows teachers or group leaders to register multiple students at once with a single payment transaction. This streamlines the onboarding process for schools and organizations.

---

## Features

### 1. **Dual Registration Modes**
- **Single Registration**: Individual scouts can register themselves
- **Batch Registration**: Teachers can register multiple students in one transaction

### 2. **Dynamic Payment Calculation**
- Base amount: ₱500.00 per student
- Total automatically calculated: `number_of_students × 500`
- Real-time total display during form filling

### 3. **Automatic Student Account Creation**
- Student accounts created automatically after payment confirmation
- Each student receives welcome email with login credentials
- All students get 'scout' rank and 'active' status

### 4. **PayMongo Integration**
- Single payment transaction for entire batch
- Supports GCash, PayMaya, and GrabPay
- Automatic webhook processing for payment confirmation

---

## Database Models

### BatchRegistration
Tracks the overall batch registration transaction.

**Fields:**
- `batch_id` (UUID): Unique identifier for the batch
- `registrar_name`: Teacher/registrar full name
- `registrar_email`: Email for notifications
- `registrar_phone`: Contact number
- `number_of_students`: Count of students in batch
- `amount_per_student`: ₱500.00 (configurable)
- `total_amount`: Auto-calculated total
- `status`: pending → paid → verified
- `paymongo_source_id`: PayMongo source reference
- `paymongo_payment_id`: PayMongo payment reference
- `verified_by`: Admin who verified (if manual)
- `created_at`, `updated_at`: Timestamps

### BatchStudentData
Stores student information before account creation.

**Fields:**
- `batch_registration`: ForeignKey to BatchRegistration
- `username`, `first_name`, `last_name`, `email`: Student credentials
- `phone_number`, `date_of_birth`, `address`: Personal details
- `password_hash`: Hashed password for account creation
- `created_user`: Link to created User account
- `created_at`: Timestamp

### RegistrationPayment (Updated)
Now supports linking to batch registrations.

**New Field:**
- `batch_registration`: Optional ForeignKey linking payment to batch

---

## User Flow

### Teacher/Registrar Workflow

1. **Navigate to Registration Page**
   - URL: `/accounts/register/`
   - Click "Batch Registration (Teachers)" radio button

2. **Fill Registrar Information**
   - Name, Email, Phone Number
   - Specify number of students (1-50)

3. **Enter Student Details**
   - For each student:
     - Username, First Name, Last Name
     - Email, Phone Number
     - Date of Birth, Address
     - Password (student will use this to login)
   - Click "Add Another Student" to add more (up to 50)
   - Click "Remove" button to delete a student

4. **Review and Submit**
   - Review total amount displayed: `₱500 × number_of_students`
   - Click "Submit Batch Registration & Proceed to Payment"

5. **Complete Payment**
   - Redirected to PayMongo checkout
   - Pay via GCash/PayMaya/GrabPay
   - Total amount charged according to student count

6. **Automatic Processing**
   - PayMongo webhook confirms payment
   - All student accounts created automatically
   - Each student receives welcome email
   - Teacher receives confirmation email

---

## Technical Implementation

### Registration View (`accounts/views.py`)

**Batch Registration Flow:**
```python
if registration_type == 'batch':
    # Validate registrar form and student formset
    # Create BatchRegistration record
    # Save student data to BatchStudentData
    # Create PayMongo source with batch metadata
    # Redirect to PayMongo checkout
```

**Metadata sent to PayMongo:**
```json
{
    "payment_type": "batch_registration",
    "batch_registration_id": "123",
    "number_of_students": 5,
    "registrar_email": "teacher@example.com"
}
```

### Webhook Handler (`payments/views.py`)

**When `payment.paid` event received:**
```python
if payment_type == 'batch_registration':
    # Update BatchRegistration status to 'paid'
    # Retrieve all BatchStudentData records
    # For each student:
        # Create User account
        # Create RegistrationPayment (linked to batch)
        # Send welcome email
    # Update BatchRegistration status to 'verified'
    # Notify registrar
    # Notify admins
```

### Forms (`accounts/forms.py`)

**BatchRegistrarForm:**
- `registration_type`: Radio select (single/batch)
- `registrar_name`, `registrar_email`, `registrar_phone`
- `number_of_students`: Integer input (1-50)
- Validation: Required fields for batch mode

**BatchStudentForm:**
- All student fields (username, name, email, etc.)
- Password field (will be hashed)
- Email and username uniqueness validation

**BatchStudentFormSet:**
- Django formset for dynamic student forms
- Minimum 1 student, no maximum (limited by UI to 50)

### Template (`accounts/templates/accounts/register.html`)

**Key Features:**
- JavaScript toggle between single/batch forms
- Dynamic form addition/removal
- Real-time total calculation
- Formset management (TOTAL_FORMS, etc.)

**JavaScript Functions:**
- `updateStudentNumbers()`: Renumber students when added/removed
- `updateTotal()`: Calculate total based on student count
- Dynamic formset field name/id updating

---

## Admin Interface

### BatchRegistration Admin
**List View:**
- Batch ID (truncated), Registrar Name, Email
- Number of Students, Total Amount
- Status Badge (color-coded)
- Created Date

**Actions:**
- Mark as verified
- Mark as rejected

**Filters:**
- Status
- Created date

**Search:**
- Batch ID, Registrar name, email, phone

### BatchStudentData Admin
**List View:**
- Student Name, Email
- Batch ID (clickable link)
- Status (Created / Pending)
- Created Date

**Filters:**
- Batch registration status
- Created date

**Read-only Fields:**
- Batch registration, created user, created at

---

## Configuration

### Amount Per Student
Default: ₱500.00

To change, update `accounts/models.py`:
```python
class BatchRegistration(models.Model):
    amount_per_student = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=500.00,  # Change here
        verbose_name="Amount per Student"
    )
```

### Maximum Students Per Batch
Default: 50 (enforced in UI and form validation)

To change, update:
1. `accounts/forms.py`: `BatchRegistrarForm.number_of_students.max_value`
2. `accounts/templates/accounts/register.html`: JavaScript validation in `add_student_btn` event

---

## Testing

### Manual Testing Checklist

**Batch Registration:**
- [ ] Toggle between single and batch registration works
- [ ] Add student button creates new student form
- [ ] Remove student button deletes form (except last one)
- [ ] Total amount updates correctly when adding/removing students
- [ ] Form validation: empty fields, duplicate emails/usernames
- [ ] PayMongo redirect works with correct total amount
- [ ] Payment confirmation triggers webhook

**Webhook Processing:**
- [ ] Student accounts created with correct data
- [ ] Passwords work for login
- [ ] Registration payments linked to batch
- [ ] Emails sent to students and registrar
- [ ] Admin notifications received

**Admin Interface:**
- [ ] BatchRegistration records display correctly
- [ ] BatchStudentData shows creation status
- [ ] Filters and search work
- [ ] Admin actions (verify/reject) work

### Test Data Example

**Batch Registration:**
```json
{
    "registrar_name": "Maria Santos",
    "registrar_email": "maria.santos@school.edu.ph",
    "registrar_phone": "+639171234567",
    "number_of_students": 3,
    "students": [
        {
            "username": "juan_cruz",
            "first_name": "Juan",
            "last_name": "Cruz",
            "email": "juan.cruz@school.edu.ph",
            "phone_number": "+639181234567",
            "date_of_birth": "2010-05-15",
            "address": "123 Main St, Manila",
            "password": "SecurePass123"
        },
        {
            "username": "pedro_reyes",
            "first_name": "Pedro",
            "last_name": "Reyes",
            "email": "pedro.reyes@school.edu.ph",
            "phone_number": "+639191234567",
            "date_of_birth": "2011-03-20",
            "address": "456 Oak Ave, Quezon City",
            "password": "SecurePass456"
        },
        {
            "username": "jose_garcia",
            "first_name": "Jose",
            "last_name": "Garcia",
            "email": "jose.garcia@school.edu.ph",
            "phone_number": "+639201234567",
            "date_of_birth": "2010-08-10",
            "address": "789 Pine Rd, Makati",
            "password": "SecurePass789"
        }
    ]
}
```

**Expected:**
- Total amount: ₱1,500.00
- 3 user accounts created after payment
- 3 RegistrationPayment records (all verified, linked to batch)
- 4 emails sent (3 to students + 1 to registrar)

---

## Troubleshooting

### Issue: Students not created after payment

**Symptoms:**
- Payment confirmed
- BatchRegistration status is 'paid'
- No user accounts created

**Solutions:**
1. Check webhook logs: `tail -f logs/webhook.log`
2. Check BatchStudentData records exist
3. Verify webhook handler is processing batch payments
4. Check for duplicate email/username conflicts
5. Review Django logs for errors

**Manual Fix:**
```bash
# Use management command to process batch
python manage.py process_batch_registration <batch_id>
```

### Issue: Payment amount incorrect

**Symptoms:**
- PayMongo shows different amount than displayed

**Solutions:**
1. Check JavaScript `updateTotal()` function
2. Verify formset TOTAL_FORMS value matches student count
3. Check BatchRegistration.save() method calculation
4. Ensure amount_per_student is correct (500.00)

### Issue: Duplicate student entries

**Symptoms:**
- Same student form appears multiple times
- Student number duplicates

**Solutions:**
1. Clear browser cache
2. Check JavaScript formset cloning logic
3. Verify form name/id attribute updates
4. Test with console.log in browser DevTools

### Issue: Email not sent

**Symptoms:**
- Accounts created but no emails received

**Solutions:**
1. Check email configuration in `settings.py`
2. Verify `NotificationService.send_email()` is not failing silently
3. Check spam folder
4. Review email server logs
5. Test with different email provider

---

## Security Considerations

### Password Handling
- Student passwords are hashed using Django's `make_password()`
- Passwords never stored in plain text
- Students should change password on first login

### Email Validation
- Unique email per student enforced at form and model level
- Email verification recommended for production

### Payment Security
- All payment processing through PayMongo (PCI-DSS compliant)
- Webhook signature verification required
- HTTPS required for production

### Data Privacy
- Student data stored securely in database
- Admin access logged via AnalyticsEvent
- GDPR/Data Privacy Act compliance recommended

---

## Future Enhancements

### Potential Features
1. **CSV Import**: Upload student list via CSV file
2. **Email Verification**: Require students to verify email before activation
3. **Bulk Password Reset**: Generate and email temporary passwords
4. **Payment Plans**: Support partial payments for large batches
5. **Group Assignment**: Auto-assign students to groups/patrols
6. **Discount Codes**: Apply discounts for large batches
7. **PDF Receipt**: Generate batch registration receipt
8. **Student Import from SIS**: Integrate with school information systems

### Scalability Improvements
1. **Async Processing**: Use Celery for student account creation
2. **Batch Email Sending**: Queue emails instead of sending immediately
3. **Database Indexing**: Optimize for large batches (1000+ students)
4. **Caching**: Cache batch registration data during payment flow

---

## API Reference (for developers)

### Create Batch Registration
```python
from accounts.models import BatchRegistration, BatchStudentData

batch = BatchRegistration.objects.create(
    registrar_name="John Teacher",
    registrar_email="john@school.com",
    number_of_students=5,
    amount_per_student=500.00
)

for student in student_list:
    BatchStudentData.objects.create(
        batch_registration=batch,
        **student  # username, first_name, etc.
    )
```

### Process Batch Payment
```python
from payments.views import handle_payment_paid

# Triggered automatically by webhook
# Or manually process:
batch.status = 'paid'
batch.save()

for student_data in batch.student_data.all():
    user = User.objects.create(...)
    student_data.created_user = user
    student_data.save()
```

### Query Batch Status
```python
# Get all pending batches
pending = BatchRegistration.objects.filter(status='pending')

# Get batch with students
batch = BatchRegistration.objects.prefetch_related('student_data').get(id=123)
students = batch.student_data.all()

# Check if students created
created_count = batch.student_data.filter(created_user__isnull=False).count()
```

---

## Support

For issues or questions:
1. Check this documentation
2. Review Django logs
3. Test in development environment first
4. Contact system administrator

---

**Last Updated:** October 17, 2025  
**Version:** 1.0.0  
**Author:** ScoutConnect Development Team
