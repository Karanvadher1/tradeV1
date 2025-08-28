from django.contrib import admin
from .models import InstrumentDetails
from .proxies import create_instrument_detail_proxy

admin.site.register(InstrumentDetails)

try:
    for instrument_code in InstrumentDetails.objects.values_list(
        "instrument_code", flat=True
    ).distinct():
        proxy_class = create_instrument_detail_proxy(instrument_code)
        admin.site.register(proxy_class)
except Exception as e:
    print(f"[ADMIN WARNING] Skipping dynamic admin registration: {e}")
