from datetime import datetime, timedelta, timezone, date

from django.db import IntegrityError
from .models import AlgoStrategy, Trade, Token, InstrumentDetails, IntradayData
from django.db.models import Min

from asgiref.sync import sync_to_async


class BrokerService:

    def create_strategy(self, name, support, resistance):
        strategy = AlgoStrategy(name=name, support=support, resistance=resistance)
        strategy.save()
        return strategy

    @sync_to_async
    def trade_exists(self, time, trade_time):
        if trade_time:
            return Trade.objects.filter(trade_time=trade_time).exists()
        if time:
            return Trade.objects.filter(time=time).exists()

    @sync_to_async
    def get_strategy_by_name(self, name):
        return AlgoStrategy.objects.filter(
            name=name
        ).first()  # important: get the actual instance

    async def create_trade(
        self,
        strike_price,
        option_chain_call_or_put,
        order_type,
        time,
        buy_at,
        target,
        sell_at,
        trade_time,
    ):
        if await self.trade_exists(time, trade_time):
            return None

        strategy = await self.get_strategy_by_name("swing")

        if not strategy:
            print("Strategy not found")
            return None

        chart = "NSE_INDEX|Nifty 50"

        trade = await sync_to_async(Trade.objects.create)(
            swing_strategy=strategy,
            chart=chart,
            strike_price=strike_price,
            option_chain_call_or_put=option_chain_call_or_put,
            order_type=order_type,
            time=time,
            buy_at=buy_at,
            target=target,
            sell_at=sell_at,
            trade_time=trade_time,
        )
        print("Trade is created", trade)
        return trade

    def save_token(self, token: dict, user: str):
        token_obj, created = Token.objects.update_or_create(
            client_id=user,
            defaults={
                "access_token": token["access_token"],
            },
        )
        return token_obj

    def get_token(self, user: str):
        return Token.objects.filter(client_id=user).first()

    def update_instrument_data(self, data):
        obj, created = InstrumentDetails.objects.update_or_create(
            instrument_key=data.get("instrument_key"),
            defaults={
                "exchange_token": data.get("exchange_token"),
                "tradingsymbol": data.get("tradingsymbol"),
                "name": data.get("name"),
                "last_price": data.get("last_price"),
                "expiry": data.get("expiry"),
                "strike": data.get("strike"),
                "lot_size": data.get("lot_size"),
                "instrument_type": data.get("instrument_type"),
                "option_type": data.get("option_type"),
                "modified_at": timezone.now(),
            },
        )
        return obj, created


class InstrumentService:
    def get_index_details(self, symbol=None):
        if symbol:
            return InstrumentDetails.objects.filter(tradingsymbol=symbol).first()
        return InstrumentDetails.objects.filter(
            instrument_type="INDEX", tradingsymbol="NIFTY"
        )

    def get_option_chain_by_strike(self, strike, option_type):
        today = datetime.now().date()

        # Find the nearest expiry greater than today
        nearest_expiry = InstrumentDetails.objects.filter(
            strike=strike, option_type=option_type, expiry__gt=today
        ).aggregate(Min("expiry"))["expiry__min"]

        if nearest_expiry:
            return InstrumentDetails.objects.filter(
                strike=strike, option_type=option_type, expiry=nearest_expiry
            ).first()
        return InstrumentDetails.objects.none()


class IntradayService:

    def create_intraday_data(self, data):
        """
        Creates or updates an intraday data record in the database.
        `data` is expected to be a dictionary with keys: instrument_key, datetime, open, high, low, close.
        """
        try:
            instrument = InstrumentDetails.objects.get(
                instrument_key=data.get("instrument_key")
            )

            # Convert Unix timestamp to a datetime object
            timestamp = int(data.get("datetime")) / 1000
            dt_object = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

            obj, created = IntradayData.objects.update_or_create(
                instrument=instrument,
                datetime=dt_object,
                defaults={
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                },
            )
            return obj, created
        except InstrumentDetails.DoesNotExist:
            print(
                f"Error: Instrument with key '{data.get('instrument_key')}' not found."
            )
            return None, False
        except IntegrityError as e:
            print(f"Database integrity error: {e}")
            return None, False
        except Exception as e:
            print(f"An unexpected error occurred while creating intraday data: {e}")
            return None, False

    def get_intraday_data(self, instrument_key):
        """
        Fetches all intraday data for a given instrument key.
        Returns a Django QuerySet.
        """
        try:
            instrument = InstrumentDetails.objects.get(instrument_key=instrument_key)

            return IntradayData.objects.filter(
                instrument=instrument, created_at__gte=date.today()
            ).order_by("datetime")
        except InstrumentDetails.DoesNotExist:
            return IntradayData.objects.none()

    def get_intraday_data_by_date(self, instrument_key, specific_date):
        """
        Fetch intraday data for a given instrument key and timestamp.
        Handles timezone correctly by querying a range.
        """
        try:
            candle_start_time = specific_date
            instrument = InstrumentDetails.objects.get(instrument_key=instrument_key)

            qs = IntradayData.objects.filter(
                instrument=instrument,
                datetime=candle_start_time,
                created_at__gte=date.today(),
            ).values("datetime", "open", "high", "low", "close")

            return qs.first() if qs.exists() else {}

        except InstrumentDetails.DoesNotExist:
            return {}  # Changed from [] to {} for consistency
        except Exception as e:
            print(f"Error fetching intraday data: {e}")
            return {}
