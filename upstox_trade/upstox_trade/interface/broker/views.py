from datetime import datetime, time, timedelta
import json
from django.shortcuts import redirect, render
import requests
from django.views.generic import RedirectView, View
from django.http import HttpResponse, JsonResponse
from decouple import config

from upstox_trade.application.broker.service import (
    BrokerAppService,
    InstrumentAppService,
)
from upstox_trade.domain.broker.tasks import fetch_and_save_upstox_instruments
from upstox_trade.application.order.services import OrderAppService

# mappings.py or inside views.py
INTERVAL_UNIT_MAP = {
    "1min": {"interval": 1, "unit": "minutes"},
    "5min": {"interval": 5, "unit": "minutes"},
    "15min": {"interval": 15, "unit": "minutes"},
    "30min": {"interval": 30, "unit": "minutes"},
    "1h": {"interval": 1, "unit": "hours"},
    "1d": {"interval": 1, "unit": "days"},
    "1wk": {"interval": 1, "unit": "weeks"},
    "1mo": {"interval": 1, "unit": "months"},
}


class UpstoxLoginView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return (
            f"{config('LOGIN_URL')}"
            f"?response_type=code"
            f"&client_id={config('CLIENT_ID')}"
            f"&redirect_uri={config('REDIRECT_URI')}"
        )


class UpstoxCallbackView(View):
    def __init__(self):
        self.broker_app_service = BrokerAppService()

    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        if not code:
            return HttpResponse("Authorization code not found!", status=400)

        token_url = config("AUTHORISATION_URL")
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": config("CLIENT_ID"),
            "client_secret": config("CLIENT_SECRET"),
            "redirect_uri": config("REDIRECT_URI"),
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(token_url, data=data, headers=headers)
        if response.status_code == 200:
            tokens = response.json()
            self.broker_app_service.save_token(tokens, config("CLIENT_ID"))
            return redirect("instrument")
        else:
            return HttpResponse(f"Token exchange failed: {response.text}", status=400)


class InstrumentView(View):
    def __init__(self, **kwargs):
        self.broker_app_service = BrokerAppService()
        self.instrument_app_service = InstrumentAppService()
        self.order_app_service = OrderAppService()

    def get(self, request):
        index = self.instrument_app_service.get_index_details()
        orders = self.order_app_service.list_all_orders()
        return render(request, "chart.html", {"index": index, "orders": orders})

    def post(self, request):
        data = json.loads(request.body)
        instrument_key = data.get("instrument_key")
        interval = data.get("interval")
        unit = data.get("unit")

        today = datetime.today().date()
        to_date = data.get("to_date") or (today - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        from_date = data.get("from_date") or (today - timedelta(days=2)).strftime(
            "%Y-%m-%d"
        )

        try:
            data = self.broker_app_service.get_instrument_historical_data(
                instrument_key, interval, unit, from_date, to_date
            )
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


class ChartView(View):
    def __init__(self, **kwargs):
        self.broker_app_service = BrokerAppService()

    def get(self, request):
        return render(request, "chart.html")

    def post(self, request):
        data = json.loads(request.body)
        instrument_key = data.get("instrument_key")
        interval = data.get("interval")
        unit = data.get("unit")
        now = datetime.now().time()
        cutoff = time(10, 30)

        if now >= cutoff:
            interval = 3
            unit = "minutes"
        try:
            data = self.broker_app_service.get_instrument_intraday_data(
                instrument_key, interval, unit
            )
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


class StreakView(View):
    def __init__(self):
        self.broker_app_service = BrokerAppService()

    def get(self, request):
        fetch_and_save_upstox_instruments.delay()

        try:
            data = self.broker_app_service.proccess_streak(
                instrument_key="25100",
                option_type="CE",
                start_time="2025-09-12 11:36:00+05:30",
                end_time="2025-09-12 11:45:00+05:30",
            )
            print(data)
            return JsonResponse(data)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


class StrategyView(View):
    def __init__(self, **kwargs):
        self.broker_app_service = BrokerAppService()

    def get(self, request):
        return render(request, "strategy.html")

    def post(self, request):
        name = request.POST.get("name")
        support = request.POST.get("support")
        resistance = request.POST.get("resistance")
        try:
            data = self.broker_app_service.create_strategy(name, support, resistance)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

        return JsonResponse(
            {
                "name": data.name,
                "support": data.support,
                "resistance": data.resistance,
            }
        )
