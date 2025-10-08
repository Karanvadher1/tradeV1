from django.urls import path
from .views import *


urlpatterns = [
    path("order/<path:instrument>", OrderView.as_view(), name="order_create"),
    path("orders/<int:order_id>/", OrderView.as_view()),
]
