from django.http import JsonResponse
from django.views import View
from upstox_trade.application.notification.services import NotificationAppService


class NotificationView(View):
    def __init__(self):
        self.notification_app_service = NotificationAppService()

    def get(self, request):
        notifications = self.notification_app_service.list_all_notifications()
        data = {
            "notifications": [
                {
                    "content": n.content,
                    "instrument": str(n.instrument.instrument_key),
                    "price": n.price,
                    "related_url": n.related_url,
                    "is_read": n.is_read,
                }
                for n in notifications
            ]
        }
        return JsonResponse(data, safe=False)

    def get_notification(self, notification_id):
        return self.notification_app_service.get_notification(notification_id)
