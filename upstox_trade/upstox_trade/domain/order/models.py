from django.db import models


class Order(models.Model):
    Transaction_TYPE_CHOICES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
    ]

    PRODUCT_TYPE_CHOICES = [
        ("I", "Intraday"),  # MIS
        ("D", "Delivery"),  # CNC
        ("MTF", "Margin"),  # NRML
    ]

    ORDER_TYPE_CHOICES = [
        ("MARKET", "MARKET"),
        ("LIMIT", "LIMIT"),
        ("SL", "SL"),
        ("SL-M", "SL-M"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PLACED", "Placed"),
        ("COMPLETE", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("REJECTED", "Rejected"),
    ]

    INSTRUMENT_TYPE_CHOICES = [
        ("CE", "Call Option"),
        ("PE", "Put Option"),
    ]

    broker_order_id = models.CharField(max_length=100, blank=True, null=True)
    symbol = models.CharField(max_length=50)  # e.g. NIFTY
    expiry = models.DateField()
    strike_price = models.FloatField()
    instrument_type = models.CharField(
        max_length=2, choices=INSTRUMENT_TYPE_CHOICES
    )  # CE/PE

    transaction_type = models.CharField(
        max_length=4, choices=Transaction_TYPE_CHOICES
    )  # BUY/SELL
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    product_type = models.CharField(max_length=3, choices=PRODUCT_TYPE_CHOICES)
    quantity = models.IntegerField()
    price = models.FloatField()  # 0 for market

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    filled_quantity = models.IntegerField(default=0)
    average_price = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.symbol} {self.strike_price}{self.instrument_type} {self.order_side} {self.quantity}"
