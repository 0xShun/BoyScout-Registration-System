from django.db import models
from accounts.models import User

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField(User, related_name='announcements', blank=True)
    read_by = models.ManyToManyField(User, related_name='read_announcements', blank=True)

    def __str__(self):
        return self.title
