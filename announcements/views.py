from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AnnouncementForm
from .models import Announcement
from accounts.models import User

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin())(view_func)

@login_required
def announcement_list(request):
    announcements = Announcement.objects.all().order_by('-date_posted')
    return render(request, 'announcements/announcement_list.html', {'announcements': announcements})

@admin_required
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save()
            messages.success(request, 'Announcement created.')
            return redirect('announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/announcement_create.html', {'form': form})

@login_required
def announcement_mark_read(request, pk):
    announcement = Announcement.objects.get(pk=pk)
    announcement.read_by.add(request.user)
    return redirect('announcement_list')
