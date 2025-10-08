import asyncio
from datetime import datetime, timedelta
import ssl
import traceback
import uuid
import json
import websockets
import aiohttp
from decouple import config
from upstox_trade.infrastructure import MarketDataFeed_pb2 as pb
from google.protobuf.json_format import MessageToDict
import upstox_client
from upstox_trade.domain.broker.services import IntradayService
from upstox_trade.application.broker.service import BrokerAppService, StretagyAppService
from asgiref.sync import sync_to_async


class TickStreamService:
    def __init__(self, instrument, use_websocket=True):
        self.instrument = instrument
        self.use_websocket = use_websocket
        self.keep_running = True
        self.intraday_service = IntradayService()
        self.day_open = None
        self.live_open = None
        self.live_high = None
        self.live_low = None
        self.live_close = None
        self.last_prev_ts = None
        self.channel_layer = None
        self.group_name = None

        self.high_3m = None
        self.low_3m = None
        self.close_3m = None
        self.candle_3m = {}

    @staticmethod
    def get_candle_start_times_to_now(
        start_hour=9, start_minute=15, interval_minutes=3
    ):
        """
        Calculates the most recent 3-minute candle start time from 9:15 AM.
        """
        now = datetime.now()
        start_of_day = now.replace(
            hour=start_hour, minute=start_minute, second=0, microsecond=0
        )

        if now < start_of_day:
            return None  # No candle has started yet today

        # Calculate total minutes elapsed since market open
        total_minutes_elapsed = (now - start_of_day).total_seconds() // 60

        # Find the number of full intervals that have passed
        intervals_passed = int(total_minutes_elapsed // interval_minutes)

        # Calculate the exact start time of the most recent candle
        most_recent_start_time = start_of_day + timedelta(
            minutes=intervals_passed * interval_minutes
        )

        return most_recent_start_time

    def decode_protobuf(self, buffer):
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(buffer)
        return feed_response

    async def save_intraday_data(self, live_candle):
        """Wrap sync ORM call into async-safe"""
        await sync_to_async(self.intraday_service.create_intraday_data)(live_candle)

    async def get_intraday_data_by_date(self, instrument_key, date):
        """Wrap sync ORM call into async-safe"""
        return await sync_to_async(self.intraday_service.get_intraday_data_by_date)(
            instrument_key, date
        )

    async def _process_tick_data(self, data_dict):
        """Processes raw tick data and updates OHLC values."""
        try:
            # await StretagyAppService().calculate_trade(
            #     instrument_key="NSE_INDEX|Nifty 50", candle=data_dict
            # )

            current_ts = int(data_dict["currentTs"])
            indexFF = data_dict["feeds"][self.instrument]["ff"]

            ltpc = indexFF["indexFF"]["ltpc"]
            ohlc = indexFF["indexFF"]["marketOHLC"]["ohlc"]

            ltp = ltpc["ltp"]
            prev_candle = ohlc[1]
            prev_candle["datetime"] = prev_candle["ts"]
            day_candle = ohlc[0]

            if self.day_open is None:
                self.day_open = day_candle["open"]

            prev_ts = int(prev_candle["ts"])
            if self.last_prev_ts is None:
                self.last_prev_ts = prev_ts
                self.live_open = ltp
                self.live_high = ltp
                self.live_low = ltp
            elif prev_ts != self.last_prev_ts:
                print(
                    f"⏱️ Prev candle changed! Old: {self.last_prev_ts}, New: {prev_ts}"
                )
                live_candle = {
                    "open": self.live_open,
                    "high": self.live_high,
                    "low": self.live_low,
                    "close": ltp,
                    "datetime": self.last_prev_ts,
                    "instrument_key": self.instrument,
                }
                self.live_open = ltp
                self.live_high = ltp
                self.live_low = ltp
                self.last_prev_ts = prev_ts

            self.live_high = max(self.live_high, ltp)
            self.live_low = min(self.live_low, ltp)

            candle_start_3_minute = self.get_candle_start_times_to_now()
            first_candle = await self.get_intraday_data_by_date(
                self.instrument, candle_start_3_minute
            )
            if first_candle == {}:
                first_candle = prev_candle

                self.high_3m = max(
                    first_candle["high"],
                    self.live_high,
                )
                self.low_3m = min(
                    first_candle["low"],
                    self.live_low,
                )
            else:
                self.high_3m = max(
                    first_candle["high"],
                    prev_candle["high"],
                    self.live_high,
                )
                self.low_3m = min(
                    first_candle["low"],
                    prev_candle["low"],
                    self.live_low,
                )
            self.live_close = ltp

            self.candle_3m = {
                "open": first_candle["open"],
                "high": self.high_3m,
                "low": self.low_3m,
                "close": self.live_close,
                "datetime": str(first_candle["datetime"]),
                "instrument_key": self.instrument,
            }

            live_candle = {
                "open": self.live_open,
                "high": self.live_high,
                "low": self.live_low,
                "close": self.live_close,
                "datetime": current_ts,
                "instrument_key": self.instrument,
            }
            await self.save_intraday_data(live_candle)
            await StretagyAppService().calculate_trade(self.instrument, prev_candle)

            if self.channel_layer and self.group_name:
                message = {
                    "type": "send_market_data",  # Matches the consumer method
                    "message": {
                        "live_candle": live_candle,
                        "prev_candle": prev_candle,
                        "candle_3m": self.candle_3m,
                    },
                }
                await self.channel_layer.group_send(self.group_name, message)

        except Exception as e:
            print("Tick stream data processing error:", e)
            print(traceback.print_exc())

    async def _websocket_loop(self):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        access_token = await sync_to_async(BrokerAppService().get_token)(
            user=config("CLIENT_ID")
        )
        configuration = upstox_client.Configuration()
        configuration.access_token = access_token
        api_client = upstox_client.ApiClient(configuration)
        api_instance = upstox_client.WebsocketApi(api_client)
        response = api_instance.get_market_data_feed_authorize("3.0")
        url = response.data.authorized_redirect_uri
        print("Connecting to Upstox WS:", url)
        async with websockets.connect(url, ssl=ssl_context) as ws:
            await ws.send(
                json.dumps(
                    {
                        "guid": str(uuid.uuid4()),
                        "method": "sub",
                        "data": {
                            "mode": "full",
                            "instrumentKeys": [self.instrument],
                        },
                    }
                ).encode("utf-8")
            )
            while self.keep_running:
                try:
                    message = await ws.recv()
                    decoded = self.decode_protobuf(message)
                    data_dict = MessageToDict(decoded)
                    await self._process_tick_data(data_dict)
                except Exception as e:
                    print("Tick stream error:", e)
                    continue

    async def _polling_loop(self):
        print("Starting polling loop...")
        polling_url = "http://127.0.0.1:8000/live-trades/"
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            while self.keep_running:
                try:
                    payload = {"instrument_key": self.instrument}
                    async with session.post(
                        polling_url, data=json.dumps(payload), headers=headers
                    ) as resp:
                        data = await resp.json()
                        await self._process_tick_data(data)
                except Exception as e:
                    print("Polling error:", e)
                await asyncio.sleep(5)

    async def start(self):
        """Keep reconnecting until stopped."""
        while self.keep_running:
            try:
                if self.use_websocket:
                    await self._websocket_loop()
                else:
                    await self._polling_loop()
            except Exception as e:
                print(f"⚠️ Connection error: {e}, retrying in 5s...")
                await asyncio.sleep(5)

    def stop(self):
        self.keep_running = False
