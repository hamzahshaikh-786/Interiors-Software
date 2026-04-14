from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(is_seen=False)
        return {
            'unread_notifications': unread_notifications,
            'unread_notifications_count': unread_notifications.count()
        }
    return {}
