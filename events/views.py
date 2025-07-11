from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Event, EventPhoto, Attendance, EventRegistration
from .forms import EventForm, EventPhotoForm, EventRegistrationForm
from accounts.views import admin_required # Reusing the admin_required decorator
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
import os
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from accounts.models import User
from django.utils import timezone
from notifications.services import send_realtime_notification, NotificationService

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

@login_required
def event_list(request):
    events = Event.objects.all().order_by('-date', '-time')
    paginator = Paginator(events, 10)
    page = request.GET.get('page')
    events = paginator.get_page(page)
    return render(request, 'events/event_list.html', {'events': events})

@admin_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            messages.success(request, 'Event created successfully.')
            return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventForm()
    return render(request, 'events/event_form.html', {'form': form})

@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    photos = event.photos.all().order_by('-is_featured', '-uploaded_at')
    # Attendance summary
    attendance_qs = event.attendances.select_related('user')
    present_list = [a.user for a in attendance_qs if a.status == 'present']
    absent_list = [a.user for a in attendance_qs if a.status == 'absent']
    present_count = len(present_list)
    absent_count = len(absent_list)
    total_scouts = present_count + absent_count

    # Registration logic
    registration = None
    registration_form = None
    if request.user.is_authenticated:
        registration = EventRegistration.objects.filter(event=event, user=request.user).first()
        if request.method == 'POST' and 'register_event' in request.POST:
            if registration:
                registration_form = EventRegistrationForm(request.POST, request.FILES, instance=registration)
            else:
                registration_form = EventRegistrationForm(request.POST, request.FILES)
            if registration_form.is_valid():
                reg = registration_form.save(commit=False)
                reg.event = event
                reg.user = request.user
                reg.save()
                messages.success(request, 'Event registration submitted!')
                return redirect('events:event_detail', pk=event.pk)
            else:
                messages.error(request, 'There was an error with your registration. Please check the form.')
        else:
            registration_form = EventRegistrationForm(instance=registration)

    # Admin: see all registrations
    registrations = None
    if request.user.is_authenticated and request.user.is_admin():
        registrations = EventRegistration.objects.filter(event=event).select_related('user')

    return render(request, 'events/event_detail.html', {
        'event': event,
        'photos': photos,
        'present_list': present_list,
        'absent_list': absent_list,
        'present_count': present_count,
        'absent_count': absent_count,
        'total_scouts': total_scouts,
        'registration': registration,
        'registration_form': registration_form,
        'registrations': registrations,
    })

@admin_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully.')
            return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {'form': form})

@admin_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully.')
        return redirect('events:event_list')
    return render(request, 'events/event_confirm_delete.html', {'event': event})

@admin_required
def photo_upload(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk)
    
    if request.method == 'POST':
        form = EventPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Validate image file
                image = request.FILES['image']
                if image.size > settings.MAX_UPLOAD_SIZE:  # e.g., 5MB
                    messages.error(request, 'Image size must be less than 5MB.')
                    return redirect('events:event_detail', pk=event.pk)
                
                # Validate image format
                try:
                    img = Image.open(image)
                    if img.format.lower() not in ['jpeg', 'jpg', 'png', 'gif']:
                        messages.error(request, 'Invalid image format. Please upload JPG, PNG, or GIF.')
                        return redirect('events:event_detail', pk=event.pk)
                except Exception as e:
                    messages.error(request, 'Invalid image file.')
                    return redirect('events:event_detail', pk=event.pk)

                # Create photo instance
                photo = form.save(commit=False)
                photo.event = event
                photo.uploaded_by = request.user
                
                # Generate unique filename
                ext = os.path.splitext(image.name)[1]
                filename = f"event_{event.pk}_photo_{photo.uploaded_at.strftime('%Y%m%d_%H%M%S')}{ext}"
                photo.image.save(filename, image, save=False)
                
                photo.save()
                messages.success(request, 'Photo uploaded successfully.')
                return redirect('events:event_detail', pk=event.pk)
                
            except Exception as e:
                messages.error(request, f'Error uploading photo: {str(e)}')
                return redirect('events:event_detail', pk=event.pk)
    else:
        form = EventPhotoForm()
    return render(request, 'events/photo_upload.html', {
        'form': form,
        'event': event
    })

@login_required
def photo_delete(request, photo_pk):
    photo = get_object_or_404(EventPhoto, pk=photo_pk)
    
    # Check if user has permission to delete the photo
    if not (request.user.is_staff or request.user == photo.uploaded_by):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        raise PermissionDenied
    
    if request.method == 'POST':
        try:
            # Delete the image file
            if photo.image:
                if default_storage.exists(photo.image.name):
                    default_storage.delete(photo.image.name)
            
            # Delete the database record
            photo.delete()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, 'Photo deleted successfully.')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=500)
            messages.error(request, f'Error deleting photo: {str(e)}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    return redirect('events:event_detail', pk=photo.event.pk)

@admin_required
def photo_toggle_featured(request, photo_pk):
    photo = get_object_or_404(EventPhoto, pk=photo_pk)
    
    if request.method == 'POST':
        try:
            # If setting as featured, unfeature other photos
            if not photo.is_featured:
                EventPhoto.objects.filter(event=photo.event, is_featured=True).update(is_featured=False)
            
            photo.is_featured = not photo.is_featured
            photo.save()
            messages.success(request, f'Photo {"featured" if photo.is_featured else "unfeatured"} successfully.')
        except Exception as e:
            messages.error(request, f'Error updating photo: {str(e)}')
    
    return redirect('events:event_detail', pk=photo.event.pk)

@admin_required
def event_attendance(request, pk):
    event = get_object_or_404(Event, pk=pk)
    scouts = User.objects.filter(rank='scout').order_by('last_name', 'first_name')
    existing_attendance = {a.user_id: a for a in Attendance.objects.filter(event=event)}

    if request.method == 'POST':
        for scout in scouts:
            status = request.POST.get(f'attendance_{scout.id}', 'absent')
            att, created = Attendance.objects.get_or_create(event=event, user=scout, defaults={
                'status': status,
                'marked_by': request.user
            })
            if not created:
                att.status = status
                att.marked_by = request.user
                att.save()
        messages.success(request, 'Attendance has been updated.')
        return redirect('events:event_attendance', pk=event.pk)

    # Prepare attendance status for display
    attendance_status = {scout.id: existing_attendance.get(scout.id).status if scout.id in existing_attendance else '' for scout in scouts}
    return render(request, 'events/event_attendance.html', {
        'event': event,
        'scouts': scouts,
        'attendance_status': attendance_status,
    })

@admin_required
def verify_event_registration(request, event_pk, reg_pk):
    registration = get_object_or_404(EventRegistration, pk=reg_pk, event_id=event_pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        if action == 'verify':
            registration.verified = True
            registration.verified_by = request.user
            registration.verification_date = timezone.now()
            registration.save()
            # Email and notification
            subject = f"Event Registration Payment Verified: {registration.event.title}"
            message = f"Your payment for event '{registration.event.title}' has been verified."
            if notes:
                message += f"\n\nAdmin notes: {notes}"
            NotificationService.send_email(subject, message, [registration.user.email])
            send_realtime_notification(registration.user.id, f"Your payment for '{registration.event.title}' has been verified.", type='event')
            messages.success(request, 'Registration payment verified.')
        elif action == 'reject':
            registration.verified = False
            registration.verified_by = request.user
            registration.verification_date = timezone.now()
            registration.save()
            # Email and notification
            subject = f"Event Registration Payment Rejected: {registration.event.title}"
            message = f"Your payment for event '{registration.event.title}' has been rejected."
            if notes:
                message += f"\n\nAdmin notes: {notes}"
            NotificationService.send_email(subject, message, [registration.user.email])
            send_realtime_notification(registration.user.id, f"Your payment for '{registration.event.title}' has been rejected.", type='event')
            messages.warning(request, 'Registration payment rejected.')
        return redirect('events:event_detail', pk=event_pk)
    return render(request, 'events/verify_event_registration.html', {'registration': registration, 'event_pk': event_pk})
