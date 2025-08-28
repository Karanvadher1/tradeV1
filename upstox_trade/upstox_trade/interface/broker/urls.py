from django.urls import path
from .views import *

urlpatterns = [
    path("", UpstoxLoginView.as_view(), name="upstox_login"),
    path("upstox/callback/", UpstoxCallbackView.as_view(), name="upstox_callback"),
    path("instrument/", InstrumentView.as_view(), name="instrument"),
    # path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("chart/", ChartView.as_view(), name="candle"),
    path("trade/", StreakView.as_view(), name="trade"),
    path("strategy/create/", StrategyView.as_view(), name="strategy_create"),
]
