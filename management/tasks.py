from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from .models import Borrow

@shared_task
def send_due_date_notifications():
    today = timezone.now().date()
    borrows = Borrow.objects.filter(due_date__date=today, return_date__isnull=True)

    for borrow in borrows:
        user = borrow.user
        send_mail(
            subject=f"Reminder: Your book '{borrow.book.title}' is due today",
            message=(
                f"Hi {user.username},\n\n"
                f"Please return '{borrow.book.title}' by today to avoid penalties."
            ),
            from_email=None,
            recipient_list=[user.email],
        )
    return f"Sent {len(borrows)} due date notifications."
