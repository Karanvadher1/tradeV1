from django.shortcuts import get_object_or_404
from upstox_trade.domain.notification.models import Notification


class NotificationService:
    """
    Service class for CRUD operations on Notification.
    """

    def create_notification(
        self,
        notification_type,
        content,
        instrument=None,
        trade=None,
        price=None,
        related_url=None,
    ):
        """
        Create and return a new Notification.
        """
        notification = Notification.objects.create(
            notification_type=notification_type,
            content=content,
            instrument=instrument,
            trade_id=trade,
            price=price,
            related_url=related_url,
        )
        return notification

    def get_notification(self, notification_id):
        """
        Retrieve a single notification by ID.
        Raises 404 if not found.
        """
        return get_object_or_404(Notification, id=notification_id)

    def get_all_notifications(self):
        """
        Retrieve all notifications.
        """
        return Notification.objects.all()

    def list_notifications(self, is_read=None, notification_type=None, limit=50):
        """
        List notifications with optional filters.
        """
        qs = Notification.objects.all()
        if is_read is not None:
            qs = qs.filter(is_read=is_read)
        if notification_type:
            qs = qs.filter(notification_type=notification_type)
        return qs[:limit]

    def update_notification(self, notification_id, **kwargs):
        """
        Update fields of a notification.
        """
        notification = get_object_or_404(Notification, id=notification_id)
        for key, value in kwargs.items():
            setattr(notification, key, value)
        notification.save()
        return notification

    def mark_as_read(self, notification_id):
        """
        Mark a notification as read.
        """
        notification = get_object_or_404(Notification, id=notification_id)
        notification.is_read = True
        notification.save()
        return notification

    def delete_notification(self, notification_id):
        """
        Delete a notification.
        """
        notification = get_object_or_404(Notification, id=notification_id)
        notification.delete()
        return True
