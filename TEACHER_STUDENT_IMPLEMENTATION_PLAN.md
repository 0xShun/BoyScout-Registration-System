# Teacher-Student Management System Implementation Plan

**Created:** December 23, 2025
**Status:** Planning Phase
**Last Updated:** December 23, 2025

---

## 📋 Overview
Implementing a teacher-student hierarchy system where teachers can create and manage student accounts, register them for events, submit payments, and mark attendance.

---

## 🎯 Core Requirements Summary

### User Roles & Permissions
- **Teacher**: New rank, can manage students they create
- **Student**: Can be created by teacher or self-register, full account access
- **Admin**: Full oversight of all users, teachers, and students

### Key Changes
1. Simplify user ranks to: `teacher`, `admin`, `scout` (remove senior_scout, patrol_leader, etc.)
2. Add teacher-student relationship via `managed_by` field
3. Teachers follow same registration flow as scouts (pay fee, admin verifies)
4. Teachers auto-approve payments they submit for their students
5. Students receive welcome email with login credentials
6. Students have full account access (can register for events, submit payments, edit profile)
7. Teacher notifications for student actions
8. CSV export with Excel format (3 sheets: student list, attendance, payments)

---

## 📊 Implementation Checklist

### Phase 1: Database Schema Changes
- [x] **1.1** Update User model - modify `RANK_CHOICES` to only include `teacher`, `admin`, `scout`
- [x] **1.2** Add `managed_by` ForeignKey field to User model (nullable, references teacher)
- [x] **1.3** Create and run migrations
- [x] **1.4** Update database_schema.dbml file
- [x] **1.5** Test migration on development database

**Status:** ✅ COMPLETED
**Files Modified:**
- `accounts/models.py` - Updated RANK_CHOICES and REGISTRATION_STATUS_CHOICES, added managed_by field
- `database_schema.dbml` - Updated enums and user table structure
- `accounts/migrations/0015_user_managed_by_alter_user_rank_and_more.py` - Created and applied

---

### Phase 2: Teacher Registration Flow
- [x] **2.1** Update registration form to include teacher rank option
- [x] **2.2** Create teacher registration view (same as scout flow)
- [x] **2.3** Update registration templates to show teacher option
- [ ] **2.4** Test teacher registration end-to-end
- [ ] **2.5** Verify teacher payment verification flow

**Status:** ⏳ IN PROGRESS (60% complete)
**Files Modified:**
- `accounts/forms.py` - Added rank choice field to UserRegisterForm
- `accounts/views.py` - Updated register view to use rank from form

---

### Phase 3: Teacher Dashboard
- [x] **3.1** Create teacher dashboard view
- [x] **3.2** Create teacher dashboard template
- [x] **3.3** Add sections:
  - [x] List of students (with status, rank, contact info)
  - [x] Create new student button
  - [x] Upcoming events
  - [x] Register students for events (link)
  - [x] Mark attendance for events (link)
  - [x] Submit payments for students (link)
  - [x] View student payment history
  - [x] Export data button
- [x] **3.4** Add URL routing for teacher dashboard
- [ ] **3.5** Test teacher dashboard access and permissions

**Status:** ⏳ IN PROGRESS (80% complete)
**Files Created:**
- `accounts/templates/accounts/teacher_dashboard.html` - Comprehensive teacher dashboard
**Files Modified:**
- `accounts/views.py` - Added teacher_dashboard view with student statistics
- `accounts/urls.py` - Added teacher-dashboard URL pattern

**Note:** URLs reference views that will be created in Phase 4-9 (student management, event registration, etc.)

---

### Phase 4: Student Management by Teachers
- [x] **4.1** Create "Create Student" form
  - Required: username (auto-generated: firstname_lastname_XXX), email, password, first_name, last_name, rank
  - Optional: date_of_birth, phone, address
- [x] **4.2** Create "Create Student" view with auto-approval logic
- [x] **4.3** Create "Edit Student" form and view
- [x] **4.4** Create "Change Student Status" view (active/inactive/graduated/suspended)
- [x] **4.5** Send welcome email with login credentials to student
- [x] **4.6** Create student list view for teachers (only their students)
- [x] **4.7** Create student detail view
- [ ] **4.8** Test student creation, editing, and status changes

**Status:** ✅ COMPLETED (90% - pending testing)
**Files Created:**
- `accounts/templates/accounts/teacher/create_student.html` - Student creation form
- `accounts/templates/accounts/teacher/edit_student.html` - Student editing form  
- `accounts/templates/accounts/teacher/student_list.html` - List of teacher's students
- `accounts/templates/accounts/teacher/student_detail.html` - Student profile details
**Files Modified:**
- `accounts/forms.py` - Added TeacherCreateStudentForm and TeacherEditStudentForm
- `accounts/views.py` - Added teacher_create_student, teacher_student_list, teacher_edit_student, teacher_student_detail views
- `accounts/urls.py` - Added URL patterns for student management

---

### Phase 5: Event Registration by Teachers
- [x] **5.1** Create bulk event registration form (select multiple students)
- [x] **5.2** Create event registration view for teachers
- [x] **5.3** Calculate total payment amount (num_students × event_fee)
- [x] **5.4** Allow single payment upload for all students
- [x] **5.5** Auto-approve payment (set verified_by = teacher_id)
- [x] **5.6** Send email notifications to students about registration
- [x] **5.7** Test bulk registration with payment

**Status:** ✅ COMPLETED
**Files Created:**
- `events/templates/events/teacher_bulk_register.html` - Bulk registration interface
- `events/templates/events/teacher_mark_attendance.html` - Attendance marking interface
**Files Modified:**
- `events/forms.py` - Added TeacherBulkEventRegistrationForm
- `events/views.py` - Added teacher_register_students_event and teacher_mark_attendance views
- `events/urls.py` - Added URL patterns for teacher event views

---

### Phase 6: Attendance Marking by Teachers
- [x] **6.1** Update attendance marking view - filter to show only teacher's students
- [x] **6.2** Create teacher-specific attendance template
- [x] **6.3** Allow teachers to mark attendance for their students only
- [x] **6.4** Ensure students can view their own attendance history
- [x] **6.5** Test attendance marking and viewing

**Status:** ✅ COMPLETED  
**Files Created:**
- Already created in Phase 5 (`events/templates/events/teacher_mark_attendance.html`)
**Files Modified:**
- Already modified in Phase 5 (`events/views.py` - teacher_mark_attendance view)

---

### Phase 7: Payment Management by Teachers
- [x] **7.1** Create payment submission form for students (teacher submits)
- [x] **7.2** Create payment submission view with auto-approval
- [x] **7.3** Set payment as verified automatically (verified_by = teacher_id)
- [x] **7.4** Create student payment history view for teachers
- [x] **7.5** Send notification to student about payment verification
- [x] **7.6** Test payment submission and auto-approval

**Status:** ✅ COMPLETED
**Files Created:**
- `payments/templates/payments/teacher_submit_payment.html` - Payment submission form with QR code display
- `payments/templates/payments/teacher_payment_history.html` - Payment history with filtering and stats
**Files Modified:**
- `payments/forms.py` - Added `TeacherPaymentForm` with student selection
- `payments/views.py` - Added `teacher_submit_payment` and `teacher_payment_history` views
- `payments/urls.py` - Added URL patterns (`teacher/submit/` and `teacher/history/`)
- `accounts/templates/accounts/teacher_dashboard.html` - Fixed payment URL to use `payments:teacher_submit_payment`

**Key Features:**
- Auto-approval: Payments submitted by teachers are automatically verified
- Student selection: Dropdown shows only teacher's active students
- QR code display: Shows active payment QR code for GCash payments
- Email notifications: Student receives email when payment is submitted
- Real-time notifications: Student gets instant notification via WebSocket
- Payment history: Filterable by student and status with pagination
- Summary statistics: Total verified/pending/rejected amounts displayed
- Receipt management: Upload and view payment receipts as thumbnails

---

### Phase 8: Notification System for Teachers
- [ ] **8.1** Create notification when student registers for event (teacher notified)
- [ ] **8.2** Create notification when student submits payment (teacher notified)
- [ ] **8.3** Create notification when student edits profile (teacher notified)
- [ ] **8.4** Create notification when payment verified for student (teacher notified)
- [ ] **8.5** Create notification when attendance marked by someone else (teacher notified)
- [ ] **8.6** Test all notification triggers

**Status:** Not Started
**Files to Modify:**
- `notifications/services.py`
- `events/views.py`
- `payments/views.py`
- `accounts/views.py`

---

### Phase 9: Data Export for Teachers
- [ ] **9.1** Install openpyxl library for Excel export
- [ ] **9.2** Create export view with 3 sheets:
  - [ ] Sheet 1: Student list with contact info
  - [ ] Sheet 2: Attendance records
  - [ ] Sheet 3: Payment history
- [ ] **9.3** Add export button to teacher dashboard
- [ ] **9.4** Test Excel file generation and download

**Status:** Not Started
**Files to Create:**
- `accounts/utils/export.py`
**Files to Modify:**
- `accounts/views.py`
- `accounts/urls.py`
- `requirements.txt`

---

### Phase 10: Admin Oversight Features
- [ ] **10.1** Create dedicated admin page showing teacher → students hierarchy
- [ ] **10.2** Create separate teacher account creation form for admins
- [ ] **10.3** Update admin dashboard with teacher statistics:
  - [ ] Total teachers, active teachers
  - [ ] Total students under teachers
  - [ ] Students per teacher (average, min, max)
  - [ ] Teacher with most students
- [ ] **10.4** Add ability for admin to view all teachers and their students
- [ ] **10.5** Add ability for admin to create teacher accounts directly
- [ ] **10.6** Test admin oversight features

**Status:** Not Started
**Files to Create:**
- `accounts/templates/admin/teacher_hierarchy.html`
- `accounts/templates/admin/create_teacher.html`
**Files to Modify:**
- `accounts/views.py`
- `accounts/urls.py`
- `analytics/views.py` (for statistics)

---

### Phase 11: Access Control & Permissions
- [ ] **11.1** Add permission decorators for teacher views
- [ ] **11.2** Ensure teachers can only see/edit their own students
- [ ] **11.3** Ensure students can access full account features
- [ ] **11.4** Add middleware to redirect users to appropriate dashboard
- [ ] **11.5** Test permission boundaries and access control

**Status:** Not Started
**Files to Modify:**
- `accounts/views.py`
- `events/views.py`
- `payments/views.py`
- `boyscout_system/middleware.py` (may need to create)

---

### Phase 12: Testing & Quality Assurance
- [ ] **12.1** Test teacher registration flow
- [ ] **12.2** Test student creation by teacher
- [ ] **12.3** Test bulk event registration
- [ ] **12.4** Test payment auto-approval
- [ ] **12.5** Test attendance marking
- [ ] **12.6** Test notifications
- [ ] **12.7** Test data export
- [ ] **12.8** Test admin oversight features
- [ ] **12.9** Test permission boundaries
- [ ] **12.10** Create test cases for new features

**Status:** Not Started
**Files to Create:**
- `tests/test_teacher_features.py`

---

## 🔄 Current Progress

**Overall Progress:** 33% (4/12 phases completed)

### Completed Tasks
- ✅ Phase 1: Database Schema Changes - User model updated with teacher rank and managed_by field
- ✅ Phase 2: Teacher Registration Flow - Registration form supports teacher rank selection  
- ✅ Phase 3: Teacher Dashboard - Dashboard created with all sections (ready for testing)
- ✅ Phase 4: Student Management - Full CRUD operations for teacher-managed students

### In Progress
- None - Ready to continue to Phase 5

### Blocked/Issues
- ⚠️ PDF libraries (xhtml2pdf) dependency issues - skipped for now, will address later
- ℹ️  Placeholder URLs in teacher dashboard (will be implemented in Phases 5-9)

---

## 📝 Notes & Decisions

### Design Decisions
1. **Username Generation:** Format will be `firstname_lastname_XXX` where XXX is a unique 3-digit number
2. **Payment Auto-Approval:** When teacher submits payment for student, it's automatically verified
3. **Student Account Access:** Students have full access (can register for events, submit payments, edit profile)
4. **Notification Method:** Email only (no SMS for now)
5. **Export Format:** Single Excel file with 3 sheets using openpyxl

### Database Schema Changes
- `User.rank` choices reduced to: `teacher`, `admin`, `scout`
- `User.managed_by` added as ForeignKey to User (nullable)
- `User.registration_status` expanded to include: `active`, `inactive`, `graduated`, `suspended`

### Dependencies to Add
- `openpyxl` for Excel file generation

---

## 🚀 Next Steps
1. Start with Phase 1: Database Schema Changes
2. Run migrations and verify database structure
3. Update existing code to handle new rank choices
4. Proceed to Phase 2: Teacher Registration Flow

---

**Last Updated:** December 23, 2025
