# Quick Start: Testing Batch Registration

## Prerequisites
- Development server running: `.venv/bin/python manage.py runserver`
- PayMongo TEST account configured
- ngrok running for webhook testing (optional for full test)

---

## Test Scenario 1: UI and Form Validation

### Steps:
1. Open browser: `http://localhost:8000/accounts/register/`

2. **Verify Single/Batch Toggle**
   - Click "Single Registration" - should show single registration form
   - Click "Batch Registration (Teachers)" - should show batch form
   - Toggle should work smoothly

3. **Test Batch Form - Add Students**
   - Fill in registrar information:
     - Name: Test Teacher
     - Email: teacher@test.com
     - Phone: +639171234567
     - Number of students: 3
   
   - Fill first student:
     - Username: student1
     - First Name: Juan
     - Last Name: Dela Cruz
     - Email: juan@test.com
     - Phone: +639181111111
     - Date of Birth: 2010-01-01
     - Address: 123 Test St
     - Password: TestPass123
   
   - Click "Add Another Student" button
   - Verify: New student form appears
   - Verify: Student number updates (Student #2)
   - Verify: Total amount updates (₱1,000.00)

4. **Test Remove Student**
   - Click "Remove" button on Student #2
   - Verify: Form removed
   - Verify: Total updates back to ₱500.00
   - Verify: Student numbers renumbered

5. **Test Total Calculation**
   - Add 4 more students (total 5)
   - Verify: Total shows ₱2,500.00
   - Verify: Count shows "Number of students: 5"

6. **Test Form Validation**
   - Try submitting with empty fields
   - Verify: Error messages appear
   - Try duplicate email
   - Verify: Validation error shows

**Expected Results:**
- ✅ Toggle works smoothly
- ✅ Add/remove students works
- ✅ Total calculates correctly: students × ₱500
- ✅ Form validation works
- ✅ UI is responsive

---

## Test Scenario 2: Payment Flow (without actual payment)

### Steps:
1. Fill complete batch form with 2 students:
   
   **Registrar:**
   - Name: Maria Santos
   - Email: maria@school.com
   - Phone: +639171234567
   
   **Student 1:**
   - Username: pedro
   - First Name: Pedro
   - Last Name: Reyes
   - Email: pedro@school.com
   - Password: Pass1234
   - DOB: 2011-01-15
   - Address: Manila
   
   **Student 2:**
   - Username: jose
   - First Name: Jose
   - Last Name: Garcia
   - Email: jose@school.com
   - Password: Pass5678
   - DOB: 2010-06-20
   - Address: Quezon City

2. Click "Submit Batch Registration & Proceed to Payment"

3. **Verify Redirect**
   - Should redirect to PayMongo checkout URL
   - OR show error if PayMongo not configured

4. **Check Database** (via admin or shell):
   ```python
   from accounts.models import BatchRegistration, BatchStudentData
   
   # Get latest batch
   batch = BatchRegistration.objects.latest('created_at')
   print(f"Batch ID: {batch.batch_id}")
   print(f"Status: {batch.status}")  # Should be 'pending'
   print(f"Students: {batch.number_of_students}")
   print(f"Total: ₱{batch.total_amount}")
   
   # Check student data
   students = batch.student_data.all()
   for s in students:
       print(f"- {s.first_name} {s.last_name} ({s.email})")
   ```

**Expected Results:**
- ✅ BatchRegistration created with status='pending'
- ✅ Total amount = ₱1,000.00 (2 students × ₱500)
- ✅ 2 BatchStudentData records created
- ✅ Student passwords are hashed
- ✅ PayMongo source created (if configured)

---

## Test Scenario 3: Admin Interface

### Steps:
1. Login to admin: `http://localhost:8000/admin/`

2. **Navigate to Batch Registrations**
   - Click "Batch registrations"
   - Verify: List shows all batches
   - Verify: Columns show: Batch ID, Name, Email, Students, Total, Status

3. **View Batch Details**
   - Click on a batch registration
   - Verify: All fields display correctly
   - Verify: Status can be changed
   - Check: PayMongo fields (if available)

4. **Navigate to Batch Student Data**
   - Click "Batch student datas"
   - Verify: Shows all students from batches
   - Verify: Creation status shown
   - Verify: Link to batch works

5. **Test Admin Actions**
   - Select a batch
   - Choose "Mark selected as verified"
   - Apply action
   - Verify: Status updates

**Expected Results:**
- ✅ Batch registrations display correctly
- ✅ Student data viewable
- ✅ Admin actions work
- ✅ Status badges show correct colors

---

## Test Scenario 4: Full Payment Flow (requires PayMongo TEST)

### Setup:
1. Ensure PayMongo TEST keys in `.env`
2. Start ngrok: `ngrok http 8000`
3. Update webhook URL in PayMongo dashboard

### Steps:
1. Create batch registration (2 students)
2. Complete actual payment via PayMongo:
   - Use TEST mode payment
   - Pay via GCash/PayMaya test

3. **Verify Webhook Processing**
   - Check server logs for webhook received
   - Check batch status updated to 'verified'

4. **Verify User Accounts Created**
   ```python
   from accounts.models import User, BatchStudentData
   
   # Check if users created
   batch_data = BatchStudentData.objects.filter(batch_registration_id=<batch_id>)
   for sd in batch_data:
       if sd.created_user:
           print(f"✓ User created: {sd.created_user.email}")
       else:
           print(f"✗ Not created: {sd.email}")
   ```

5. **Verify Emails Sent**
   - Check email inbox (if configured)
   - Or check console output for email content

6. **Test Student Login**
   - Logout from admin
   - Try logging in as created student
   - Use: email and password from registration

**Expected Results:**
- ✅ Webhook received and processed
- ✅ Batch status = 'verified'
- ✅ All student User accounts created
- ✅ RegistrationPayments created for each student
- ✅ Emails sent to students and registrar
- ✅ Students can login successfully

---

## Test Scenario 5: Edge Cases

### Test 1: Duplicate Email
1. Start batch registration
2. Add student with email: test@example.com
3. Add another student with SAME email
4. Try to submit
5. **Expected:** Validation error on duplicate email

### Test 2: Maximum Students
1. Set number of students to 50
2. Try adding 51st student
3. **Expected:** Alert "Maximum 50 students allowed"

### Test 3: Minimum Students
1. Create batch with 1 student
2. Try to remove the last student
3. **Expected:** Cannot remove (minimum 1)

### Test 4: Single Registration Still Works
1. Go to registration page
2. Select "Single Registration"
3. Complete single registration
4. **Expected:** Works as before, not affected by batch feature

---

## Verification Checklist

### Database
- [ ] BatchRegistration table exists
- [ ] BatchStudentData table exists
- [ ] RegistrationPayment has batch_registration field
- [ ] Migrations applied successfully

### Forms
- [ ] BatchRegistrarForm validates correctly
- [ ] BatchStudentFormSet handles multiple students
- [ ] Form errors display properly

### Views
- [ ] register() handles both single and batch
- [ ] Batch creates correct database records
- [ ] PayMongo integration works for batch
- [ ] Webhook processes batch payments

### Template
- [ ] Toggle between single/batch works
- [ ] JavaScript adds/removes students
- [ ] Total calculation is real-time and accurate
- [ ] Form submission works

### Admin
- [ ] BatchRegistration admin displays correctly
- [ ] BatchStudentData admin shows students
- [ ] Admin actions work (verify/reject)

### Payment
- [ ] Total amount calculated correctly
- [ ] PayMongo receives correct amount
- [ ] Webhook creates all student accounts
- [ ] Emails sent to all parties

---

## Quick Database Check

```bash
# Django shell
.venv/bin/python manage.py shell
```

```python
from accounts.models import *

# Count records
print(f"Batch Registrations: {BatchRegistration.objects.count()}")
print(f"Batch Student Data: {BatchStudentData.objects.count()}")

# Latest batch
batch = BatchRegistration.objects.latest('created_at')
print(f"\nLatest Batch:")
print(f"  ID: {batch.batch_id}")
print(f"  Registrar: {batch.registrar_name}")
print(f"  Students: {batch.number_of_students}")
print(f"  Total: ₱{batch.total_amount}")
print(f"  Status: {batch.status}")

# Students in batch
print(f"\nStudents:")
for s in batch.student_data.all():
    status = "✓ Created" if s.created_user else "✗ Pending"
    print(f"  - {s.first_name} {s.last_name} ({s.email}) - {status}")
```

---

## Common Issues & Fixes

### Issue: "Total amount shows NaN"
**Fix:** Check JavaScript console, ensure student count is valid number

### Issue: "Cannot add student"
**Fix:** Check browser console for JS errors, verify formset management form

### Issue: "Payment redirect fails"
**Fix:** Verify PayMongo API keys in .env, check server logs for errors

### Issue: "Students not created after payment"
**Fix:** 
1. Check webhook logs
2. Verify BatchStudentData records exist
3. Run: `python manage.py process_batch_registration <batch_id>`

### Issue: "Duplicate key error"
**Fix:** Check for existing users with same email/username

---

## Success Criteria

✅ **UI Works:**
- Toggle switches between modes
- Add/remove students functional
- Total updates in real-time

✅ **Data Saved:**
- BatchRegistration created
- BatchStudentData saved
- Passwords hashed

✅ **Payment Flow:**
- PayMongo integration works
- Correct amount charged
- Webhook processes successfully

✅ **Accounts Created:**
- All student Users created
- RegistrationPayments linked
- Students can login

✅ **Notifications:**
- Students receive welcome emails
- Registrar receives confirmation
- Admins notified

---

## Next Steps After Testing

1. **If Tests Pass:**
   - Mark feature as ready
   - Document any configuration needed
   - Create user guide for teachers

2. **If Issues Found:**
   - Note specific error messages
   - Check Django logs
   - Review webhook logs
   - Test in isolation

3. **Before Production:**
   - Switch to PayMongo LIVE keys
   - Configure production email server
   - Update webhook URL to production
   - Test with small batch first

---

**Happy Testing! 🎉**

For detailed documentation, see:
- `BATCH_REGISTRATION_GUIDE.md` - Complete feature guide
- `BATCH_REGISTRATION_SUMMARY.md` - Implementation summary
