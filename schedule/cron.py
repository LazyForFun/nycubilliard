from django.utils import timezone
from .models import Announcement

def delete_expired_announcements():
    today = timezone.now().date()
    Announcement.objects.filter(due_date__lt=today).delete()
