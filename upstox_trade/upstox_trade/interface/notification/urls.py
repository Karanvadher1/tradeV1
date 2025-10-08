from django.urls import path
from .views import *


urlpatterns = [
    path("notifications/", NotificationView.as_view(), name="notifications"),
]
