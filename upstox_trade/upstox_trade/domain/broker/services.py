from datetime import timezone
from .models import AlgoStrategy, Trade, Token, InstrumentDetails
from asgiref.sync import sync_to_async


class MarketFeedProcessor:
    @staticmethod
    def process(feed_response):
        """
        Convert protobuf FeedResponse → clean dict
        """
        from google.protobuf.json_format import MessageToDict

        data_dict = MessageToDict(feed_response)

        # Example: only extract candles for Nifty 50
        feeds = data_dict.get("feeds", {})
        nifty_feed = feeds.get("NSE_INDEX|Nifty 50", {})
        ohlc = (
            nifty_feed.get("ff", {})
            .get("indexFF", {})
            .get("marketOHLC", {})
            .get("ohlc", [])
        )

        candle_data = []
        for entry in ohlc:
            candle_data.append(
                {
                    "open": entry["open"],
                    "high": entry["high"],
                    "low": entry["low"],
                    "close": entry["close"],
                    "volume": entry.get("volume"),
                    "datetime": int(entry["ts"]),
                }
            )

        return candle_data


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

    def get_index_details(self):
        return InstrumentDetails.objects.filter(instrument_type="INDEX")
