from announcements.models import Announcement


def announcements_unread(request):
    """Provide unread announcements count for the current user."""
    if request.user and request.user.is_authenticated:
        # Count announcements that the user hasn't read yet
        unread_count = Announcement.objects.exclude(read_by=request.user).count()
        return {"unread_announcements_count": unread_count}
    return {"unread_announcements_count": 0}
