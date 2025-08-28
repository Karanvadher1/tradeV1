from django.apps import AppConfig


class BrokerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "upstox_trade.domain.broker"

    def ready(self):
        from .models import InstrumentDetails
        from .proxies import create_instrument_detail_proxy

        try:
            types = InstrumentDetails.objects.values_list("type", flat=True).distinct()
            for type_name in types:
                if type_name:
                    create_instrument_detail_proxy(type_name)
        except Exception as e:
            print(f"[INIT WARNING] Proxy not loaded: {e}")
