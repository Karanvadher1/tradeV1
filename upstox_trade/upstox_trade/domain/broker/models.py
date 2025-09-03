from django.db import models


class AlgoStrategy(models.Model):
    name = models.CharField(max_length=100)
    support = models.FloatField()
    resistance = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Trade(models.Model):
    swing_strategy = models.ForeignKey(AlgoStrategy, on_delete=models.CASCADE)
    chart = models.CharField(max_length=200)
    strike_price = models.FloatField()
    option_chain_call_or_put = models.CharField(max_length=20)
    order_type = models.CharField(max_length=20)
    time = models.CharField(max_length=200, unique=True)
    buy_at = models.FloatField()
    target = models.FloatField()
    sell_at = models.FloatField()
    trade_time = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class InstrumentDetails(models.Model):
    instrument_key = models.CharField(max_length=200)
    exchange_token = models.CharField(max_length=200)
    tradingsymbol = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    last_price = models.FloatField()
    expiry = models.CharField(max_length=200)
    strike = models.FloatField()
    lot_size = models.FloatField()
    instrument_type = models.CharField(max_length=200)
    option_type = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


# class Broker(models.Model):
#     name = models.CharField(max_length=100)
#     client_id = models.CharField(max_length=100)
#     client_secret = models.CharField(max_length=100)
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)


class Token(models.Model):
    client_id = models.CharField(max_length=200, unique=True)
    access_token = models.CharField(max_length=512)
    refresh_token = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class IntradayData(models.Model):
    instrument = models.ForeignKey(InstrumentDetails, on_delete=models.CASCADE)
    datetime = models.DateTimeField()
    open = models.FloatField()
    close = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensures that each instrument has only one entry per specific datetime
        unique_together = ("instrument", "datetime")

    def __str__(self):
        return f"{self.instrument.instrument_key} at {self.datetime}"
