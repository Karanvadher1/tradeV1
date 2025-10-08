from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

from upstox_trade.domain.broker.models import InstrumentDetails, Trade


class Notification(models.Model):
    # The type of notification, specific to trading events.
    NOTIFICATION_TYPES = (
        ("order_fill", "Order Fill"),
        ("price_alert", "Price Alert"),
        ("trade_execution", "Trade Execution"),
        ("margin_call", "Margin Call"),
        ("account_update", "Account Update"),
        ("system_message", "System Message"),
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        help_text="The type of trading event notification.",
    )

    # The content of the notification.
    content = models.TextField(help_text="The text content of the notification.")

    # Optional fields to link to specific trading data.
    instrument = models.ForeignKey(InstrumentDetails, on_delete=models.CASCADE)

    trade_id = models.ForeignKey(
        Trade, on_delete=models.CASCADE, unique=True, blank=True, null=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Price associated with the notification (e.g., alert price).",
    )

    # A link to the page related to the notification.
    related_url = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        help_text="URL to the relevant trade or account page.",
    )

    # Status of the notification.
    is_read = models.BooleanField(
        default=False, help_text="Indicates whether the user has read the notification."
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="The timestamp when the notification was created."
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Trading Notification"
        verbose_name_plural = "Trading Notifications"

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.get_notification_type_display()} for {self.instrument.tradingsymbol}"
