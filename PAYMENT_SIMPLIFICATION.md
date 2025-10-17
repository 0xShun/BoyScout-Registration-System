# Payment Simplification - Full Payment Only

## Overview
All payment iterations for both platform registration and event registration have been simplified to enforce **full payment only**. No more pending or partial payment states.

## Changes Made

### 1. Event Registration Model (`events/models.py`)
**PAYMENT_STATUS_CHOICES updated:**
- ❌ Removed: `'pending'` and `'partial'`
- ✅ Kept: `'not_required'`, `'paid'`, `'rejected'`

**Logic Changes:**
- New registrations with payment required start as `'not_required'` (unpaid)
- PayMongo webhook marks them as `'paid'` after full payment confirmation
- No intermediate pending/partial states

### 2. Database Migrations
**Created 2 migrations:**
- `0010_remove_pending_partial_payments.py` - Schema change (field choices updated)
- `0011_migrate_event_payment_statuses.py` - Data migration

**Migration Results:**
- Migrated 0 pending payments → `not_required`
- Migrated 1 partial payment → `not_required`

All existing pending/partial payments now require full payment to be marked as paid.

### 3. Dashboard Updates (`accounts/views.py`)

#### Scout Dashboard
- ❌ Removed: `pending_event_payments` context variable
- ✅ Added: `unpaid_event_registrations` (payment_status='not_required')
- Shows events that require full payment but haven't been paid yet

#### Admin Dashboard
- ❌ Removed: `payment_pending` count
- ✅ Added: `unpaid_count` for platform registrations (pending + for_verification)
- Comment clarifies: "No pending payments - all payments are full payment upfront"

### 4. Event Registration Views (`events/views.py`)

#### Event Registration Submission
**Before:**
- Set payment_status = 'pending' for events requiring payment
- Sent admin notifications for pending payments
- Showed "pending verification" messages

**After:**
- Set payment_status = 'not_required' (until webhook confirms)
- Message: "Please complete the full payment to confirm your registration"
- No pending status notifications

#### Pending Payments View
**Before:**
- Filtered for `payment_status__in=['pending', 'partial']`

**After:**
- Filters for `payment_status='not_required'` AND `event__payment_amount__gt=0`
- Shows all unpaid event registrations requiring full payment
- Renamed conceptually to "unpaid registrations"

### 5. Payment Summary (`payments/views.py`)

**Event Payment Summary Updated:**
- ❌ Removed: `'pending_events'` count
- ✅ Added: `'unpaid_events'` count (payment_status='not_required')
- Comment: "# Full payment required"

### 6. Member Detail View (`accounts/views.py`)

**Event Dues Calculation Updated:**
- ❌ Old: Calculated dues from `payment_status__in=['pending', 'partial']` with `amount_remaining`
- ✅ New: Calculates unpaid events from `payment_status='not_required'` with full `event.payment_amount`

**Logic:**
- No more partial payment tracking
- Either fully paid or fully unpaid
- Cleaner calculation: sum of unpaid event amounts

## Payment Flow

### Platform Registration
1. User registers → status: `'inactive'`
2. User pays via PayMongo → webhook confirms
3. Status updated to: `'active'`
4. **No pending intermediate state**

### Event Registration
1. User registers for event → payment_status: `'not_required'`
2. User pays full amount via PayMongo
3. Webhook confirms → payment_status: `'paid'`
4. **No pending/partial intermediate states**

## Benefits

### For Users
- ✅ Clear payment status: either paid or not paid
- ✅ No confusion about partial payments
- ✅ Immediate activation after full payment

### For Admins
- ✅ Simpler payment tracking
- ✅ No need to manage partial payments
- ✅ Clean "pay in full" model
- ✅ Reduced administrative overhead

### For Developers
- ✅ Fewer edge cases to handle
- ✅ Simpler status logic
- ✅ Reduced code complexity
- ✅ Better alignment with PayMongo flow

## Testing Checklist

### Event Registration
- [ ] Register for free event → payment_status should be 'not_required' and verified
- [ ] Register for paid event → payment_status should be 'not_required' (unpaid)
- [ ] Complete PayMongo payment → webhook should update to 'paid'
- [ ] Dashboard should show unpaid events correctly
- [ ] Admin pending payments page should show unpaid registrations

### Platform Registration
- [ ] New user registers → status should be 'inactive'
- [ ] Complete PayMongo payment → webhook should update to 'active'
- [ ] No pending status should appear

### Dashboard Display
- [ ] Scout dashboard shows unpaid event registrations
- [ ] Admin dashboard shows unpaid_count for platform registrations
- [ ] Member detail page calculates event dues correctly
- [ ] Payment summary shows unpaid_events instead of pending_events

### Migration Verification
- [ ] All old 'pending' payments converted to 'not_required'
- [ ] All old 'partial' payments converted to 'not_required'
- [ ] Existing 'paid' and 'rejected' statuses unchanged
- [ ] No data loss during migration

## Files Modified

### Models
- `events/models.py` - EventRegistration.PAYMENT_STATUS_CHOICES simplified
- `events/models.py` - update_payment_status() logic updated
- `events/models.py` - save() method updated for new registrations

### Views
- `accounts/views.py` - scout_dashboard() updated
- `accounts/views.py` - admin_dashboard() updated
- `accounts/views.py` - member_detail() event dues calculation updated
- `events/views.py` - event registration submission updated
- `events/views.py` - pending_payments() view updated
- `payments/views.py` - event payment summary updated

### Migrations
- `events/migrations/0010_remove_pending_partial_payments.py` - Schema change
- `events/migrations/0011_migrate_event_payment_statuses.py` - Data migration

## Migration Commands Run

```bash
# Create schema migration
python manage.py makemigrations events --name remove_pending_partial_payments

# Create data migration
python manage.py makemigrations events --empty --name migrate_event_payment_statuses

# Apply migrations
python manage.py migrate events
```

**Results:**
```
Operations to perform:
  Apply all migrations: events
Running migrations:
  Applying events.0010_remove_pending_partial_payments... OK
  Applying events.0011_migrate_event_payment_statuses...
    Migrated 0 pending payments to not_required
    Migrated 1 partial payments to not_required
 OK
```

## Next Steps

### Templates Update (Not Yet Done)
The following templates may still reference pending/partial payments and should be reviewed:
- `accounts/templates/accounts/scout_dashboard.html` - Update to use `unpaid_event_registrations`
- `accounts/templates/accounts/admin_dashboard.html` - Update to use `unpaid_count`
- `events/templates/events/pending_payments.html` - Update labels and messaging
- `events/templates/events/event_detail.html` - Update payment status displays
- `payments/templates/payments/payment_list.html` - Update event payment summary display

### Test Files Update (Not Yet Done)
The following test files may use old status values:
- `test_payment_auto.py` - May reference 'pending' status
- `test_complete_payment_flow.py` - May reference 'pending' status
- `test_registration_flow.py` - May use old registration statuses

## Important Notes

1. **No Partial Payments**: The system now only supports full payment. Users must pay the complete amount to be marked as paid.

2. **'not_required' Dual Meaning**:
   - For free events: means no payment needed (verified=True)
   - For paid events: means not paid yet (verified=False)
   - Check `event.payment_amount > 0` to distinguish

3. **Webhook Dependency**: All event payments are now processed through PayMongo webhooks. Direct manual verification should update payment_status to 'paid' directly.

4. **Backward Compatibility**: Template variable names like `pending_event_payments` have been updated to `unpaid_event_registrations` in views, but template files need manual updates.

---
**Last Updated:** $(date)
**Migration Status:** ✅ Complete
**Testing Status:** ⚠️ Pending
