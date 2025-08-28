from .models import InstrumentDetails
from django.db import models

_proxy_cache = {}


def create_instrument_detail_proxy(instrument_code: str):
    class_name = instrument_code.capitalize()

    if class_name in _proxy_cache:
        return _proxy_cache[class_name]

    manager_class = type(
        f"{class_name}Manager",
        (models.Manager,),
        {
            "get_queryset": lambda self: super(type(self), self)
            .get_queryset()
            .filter(intrument_code=instrument_code)
        },
    )

    proxy_class = type(
        class_name,
        (InstrumentDetails,),
        {
            "objects": manager_class(),
            "__module__": InstrumentDetails.__module__,
            "Meta": type("Meta", (), {"proxy": True}),
            "save": lambda self, *args, **kwargs: (
                setattr(self, "type", instrument_code)
                or super(type(self), self).save(*args, **kwargs)
            ),
        },
    )

    _proxy_cache[class_name] = proxy_class
    return proxy_class
