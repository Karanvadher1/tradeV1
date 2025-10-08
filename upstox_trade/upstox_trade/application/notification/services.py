from typing import Dict, Any, List
from upstox_trade.domain.notification.services import NotificationService


class NotificationAppService:
    """
    Application layer service for managing Trading Notifications.
    Uses NotificationService (domain service) for DB operations.
    """

    def __init__(self):
        self.notification_service = NotificationService()

    def get_instrument(self):
        from upstox_trade.application.broker.service import InstrumentAppService

        return InstrumentAppService().get_index_details()

    def create_notification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a notification after validating and processing input data.
        """
        instrument = self.get_instrument()
        notification = self.notification_service.create_notification(
            notification_type=data.get("notification_type"),
            content=data.get("content"),
            instrument=instrument,
            trade=data.get("trade"),
            price=data.get("price"),
            related_url=data.get("related_url"),
        )
        return NotificationAppService._to_dict(notification)

    def get_notification(self, notification_id: int) -> Dict[str, Any]:
        """
        Retrieve a notification by ID and format output.
        """
        notification = self.notification_service.get_notification(notification_id)
        return NotificationAppService._to_dict(notification)

    def list_all_notifications(self):
        """
        Get all notifications and return as list of dicts.
        """
        qs = self.notification_service.get_all_notifications()
        return qs

    def list_notifications(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get filtered notifications and return as list of dicts.
        """
        qs = self.notification_service.list_notifications(
            is_read=filters.get("is_read"),
            notification_type=filters.get("notification_type"),
            limit=filters.get("limit", 50),
        )
        return [NotificationAppService._to_dict(n) for n in qs]

    def update_notification(
        self, notification_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a notification with provided fields.
        """
        instrument = self.get_instrument()
        data.pop("instrument", instrument)
        notification = self.notification_service.update_notification(
            notification_id, **data, instrument=instrument
        )
        return NotificationAppService._to_dict(notification)

    def mark_as_read(self, notification_id: int) -> Dict[str, Any]:
        """
        Mark notification as read and return updated object.
        """
        notification = self.notification_service.mark_as_read(notification_id)
        return NotificationAppService._to_dict(notification)

    def delete_notification(self, notification_id: int) -> bool:
        """
        Delete a notification.
        """
        return self.notification_service.delete_notification(notification_id)

    # ---------- Internal helper ----------
    @staticmethod
    def _to_dict(notification) -> Dict[str, Any]:
        """
        Convert model instance into dict (DTO for frontend/API).
        """
        return {
            "id": notification.id,
            "notification_type": notification.notification_type,
            "content": notification.content,
            "instrument": (
                notification.instrument.tradingsymbol
                if notification.instrument
                else None
            ),
            "trade_id": notification.trade_id.id if notification.trade_id else None,
            "price": float(notification.price) if notification.price else None,
            "related_url": notification.related_url,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        }
