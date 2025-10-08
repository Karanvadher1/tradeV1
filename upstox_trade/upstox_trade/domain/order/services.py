from django.core.exceptions import ObjectDoesNotExist
from upstox_trade.domain.order.models import Order


class OrderService:
    """
    Domain layer service for handling Order CRUD operations.
    """

    def create_order(self, data: dict) -> Order:
        order = Order.objects.create(**data)
        return order

    def get_order(self, order_id: int) -> Order:
        try:
            return Order.objects.get(id=order_id)
        except ObjectDoesNotExist:
            return None

    def list_orders(self, filters: dict = None):
        if filters:
            return Order.objects.filter(**filters)
        return Order.objects.all()

    def update_order(self, order_id: int, data: dict) -> Order:
        try:
            order = Order.objects.get(id=order_id)
            for key, value in data.items():
                setattr(order, key, value)
            order.save()
            return order
        except ObjectDoesNotExist:
            return None

    def delete_order(self, order_id: int) -> bool:
        try:
            order = Order.objects.get(id=order_id)
            order.delete()
            return True
        except ObjectDoesNotExist:
            return False
