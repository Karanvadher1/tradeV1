import json
import re
import requests
from upstox_trade.domain.order.services import OrderService
from django.db import transaction

from upstox_trade.application.broker.service import InstrumentAppService


class OrderApiService:
    """
    API layer for handling Order workflows.
    Uses the application layer (OrderAppService).
    """

    def __init__(self):
        self.place_order_api = "https://api-sandbox.upstox.com/v3/order/place"
        self.modify_order_api = "https://api-sandbox.upstox.com/v3/order/modify"
        self.cancel_order_api = "https://api-sandbox.upstox.com/v3/order/cancel"
        self.exit_all_positions_api = "https://api.upstox.com/v2/order/positions/exit"
        self.order_details_api = "https://api.upstox.com/v2/order/details"
        self.order_history_api = "https://api.upstox.com/v2/order/history"
        self.order_book_api = "https://api.upstox.com/v2/order/retrieve-all"
        self.trade_history_api = "https://api.upstox.com/v2/charges/historical-trades"

        self.access_token = "Bearer eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzSkNRWDQiLCJqdGkiOiI2OGI4MThlNjlmYjBhNTNjOTIxNTkyMWUiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzU2ODk1NDYyLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NTk0NDI0MDB9.MvghRu4OJz0rXcfEwMUqLheU-XVWJg_zzkiG0jqtQOg"

    def handle_response(self, response):
        response_json = response.json()
        if response_json["status"] == "success":
            return response_json["data"]
        elif response_json["status"] == "error":
            return response_json["error"][0]["message"]
        else:
            return "Something went wrong"

    def place_order(self, data: dict):
        """
        Place order in upstox

        Args:
            data = json.dumps({
                "quantity": 1,
                "product": "D",
                "validity": "DAY",
                "price": 0,
                "tag": "string",
                "instrument_token": "NSE_EQ|INE848E01016",
                "order_type": "MARKET",
                "transaction_type": "BUY",
                "disclosed_quantity": 0,
                "trigger_price": 0,
                "is_amo": False,
                "slice": True
            })

        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.access_token,
        }
        url = self.place_order_api
        payload = json.dumps(data)
        response = requests.request("POST", url, headers=headers, data=payload)
        return self.handle_response(response)

    def modify_order(self, data: dict):
        """
        Modify an existing order

        Args:
            payload = json.dumps({
                "quantity": 1,
                "validity": "DAY",
                "price": 120.01,
                "order_id": "1644490272000",
                "order_type": "MARKET",
                "disclosed_quantity": 0,
                "trigger_price": 0
            })
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.access_token,
        }
        url = self.place_order_api
        payload = json.dumps(data)
        response = requests.request("PUT", url, headers=headers, data=payload)
        return self.handle_response(response)

    def cancel_order(self, order_id: int):
        """
        Cancel an existing order
        """
        headers = {
            "Authorization": self.access_token,
        }
        url = f"{self.cancel_order_api}?order_id={order_id}"
        payload = json.dumps({})
        response = requests.request("DELETE", url, headers=headers, data=payload)
        return self.handle_response(response)

    def exit_all_positions():
        """
        Use this API to exit all open positions in one go
        """
        pass

    def get_order_details(self, order_id: int):
        """
        API to retrieve the latest status of a specific order.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.access_token,
        }
        url = f"{self.order_details_api}?order_id={order_id}"
        payload = json.dumps({})
        response = requests.request("POST", url, headers=headers, data=payload)
        return self.handle_response(response)

    def get_order_history(self, order_id: int):
        """
        API to retrieve the details of a specific order.
        """
        pass

    def get_order_book(self):
        """
        API to retrieve the list of a orders placed for the current day
        """
        pass

    def get_trade_history(self):
        """
        API provides users with access to their historical trade and transaction data
        """
        pass


class OrderAppService:
    """
    Application layer for handling Order workflows.
    Uses the domain layer CRUD (OrderService).
    """

    def __init__(self):
        self.order_service = OrderService()
        self.order_api_service = OrderApiService()
        self.instrument_app_service = InstrumentAppService()

    @transaction.atomic
    def place_order(self, data: dict):
        """
        Create & place a new order (default status = PLACED).
        """
        # symbol = "NIFTY25DEC27000CE"
        # data["symbol"] = symbol
        # instument = self.instrument_app_service.get_index_details(symbol=symbol)
        # data["quantity"] = data["quantity"] * instument.lot_size
        # data["expiry"] = instument.expiry
        # data["strike_price"] = instument.strike
        # data["instrument_type"] = instument.option_type
        # data["broker_order_id"] = 123
        # data["status"] = "PLACED"
        # data["filled_quantity"] = 0
        # data["average_price"] = 0
        # order = self.order_service.create_order(data)
        # order_dict = {
        #     "quantity": int(order.quantity),
        #     "product": order.product_type,
        #     "validity": "DAY",
        #     "price": order.price,
        #     "tag": "tag",
        #     "instrument_token": instument.instrument_key,
        #     "order_type": order.order_type,
        #     "transaction_type": order.transaction_type,
        #     "disclosed_quantity": 0,
        #     "trigger_price": 0,
        #     "is_amo": False,
        #     "slice": True,
        # }
        # # TODO: integrate with broker API if required
        # response = self.order_api_service.place_order(order_dict)
        # order_id = response["order_ids"][0]
        # self.update_order(order.id, {"broker_order_id": order_id})
        # order_details = self.get_order_details(order_id=order_id)
        # return response
        order_id = 250917125858438
        # self.update_order(order_id, {"broker_order_id": order_id})
        order_details = self.cancel_order(order_id=order_id)
        return order_details

    def get_order_details(self, order_id: int):
        """
        Get details of a single order.
        """
        order_details = self.order_api_service.get_order_details(order_id=order_id)
        return order_details

    def list_all_orders(self, filters: dict = None):
        """
        List all orders (optionally with filters).
        """
        return self.order_service.list_orders(filters)

    def update_order(self, order_id: int, data: dict):
        """
        Update an existing order.
        """
        return self.order_service.update_order(data)

    @transaction.atomic
    def update_order_status(self, order_id: int, new_status: str):
        """
        Update the status of an order (Pending → Placed → Completed).
        """
        order = self.order_service.get_order(order_id)
        if not order:
            return None

        order = self.order_service.update_order(order_id, {"status": new_status})
        return order

    @transaction.atomic
    def cancel_order(self, order_id: int):
        """
        Cancel an order if it's not completed/rejected.
        """
        self.order_api_service.cancel_order(order_id)

        order = self.order_service.get_order(order_id)
        if not order:
            return None

        if order.status in ["COMPLETE", "REJECTED"]:
            return None  # cannot cancel completed/rejected order

        return self.order_service.update_order(order_id, {"status": "CANCELLED"})

    @transaction.atomic
    def delete_order(self, order_id: int):
        """
        Delete order (hard delete).
        """
        return self.order_service.delete_order(order_id)
