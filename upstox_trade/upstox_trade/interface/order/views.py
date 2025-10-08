import json
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.db import transaction

from upstox_trade.application.order.services import OrderAppService


class OrderView(View):

    def __init__(self):
        self.order_app_service = OrderAppService()

    def get(self, request, instrument):
        instrument = instrument.rstrip("/")
        # Render the order page with a form
        return render(request, "orders/create.html", {"instrument": instrument})

    def post(self, request, instrument):
        try:
            data = (
                json.loads(request.body)
                if request.content_type == "application/json"
                else request.POST.dict()
            )
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

        try:
            with transaction.atomic():
                order = self.order_app_service.place_order(data)
            return JsonResponse(
                {
                    "success": True,
                    "order_id": order["order_ids"],
                },
                status=201,
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    def put(self, request, order_id):
        try:
            data = (
                json.loads(request.body)
                if request.content_type == "application/json"
                else request.POST.dict()
            )
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

        try:
            with transaction.atomic():
                self.order_app_service.update_order(order_id, data)
            return JsonResponse({"success": True}, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    def delete(self, request, order_id):
        try:
            with transaction.atomic():
                self.order_app_service.cancel_order(order_id)
            return JsonResponse({"success": True}, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
