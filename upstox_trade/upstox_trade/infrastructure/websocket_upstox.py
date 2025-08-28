# websocket_upstox.py

import traceback
from upstox_trade.application.broker.service import BrokerAppService
import asyncio
import json
import ssl
import uuid
import upstox_client
from channels.generic.websocket import AsyncWebsocketConsumer
from google.protobuf.json_format import MessageToDict
import websockets
from upstox_trade.infrastructure import MarketDataFeed_pb2 as pb
from decouple import config
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

from upstox_trade.application.broker.service import BrokerAppService
from upstox_trade.domain.broker.services import BrokerService


class UpstoxConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.instrument_key = None
        self.keep_streaming = True
        self.upstox_task = None
        self.upstox_websocket = None

        # Get initial instrument from query
        query_string = self.scope.get("query_string", b"").decode()
        qs = parse_qs(query_string)
        instrument_values = qs.get("instrument", [])
        if instrument_values:
            self.instrument_key = instrument_values[0]
            print("Initial instrument:", self.instrument_key)
            self.upstox_task = asyncio.create_task(
                self.fetch_market_data(self.instrument_key)
            )

    # async def disconnect(self, close_code):
    #     print("Client disconnected. Reason:", close_code)

    def get_market_data_feed_authorize(self, api_version, configuration):
        api_instance = upstox_client.WebsocketApi(
            upstox_client.ApiClient(configuration)
        )
        return api_instance.get_market_data_feed_authorize(api_version)

    @database_sync_to_async
    def get_access_token(self):
        return BrokerAppService().get_token(user=config("CLIENT_ID"))

    def decode_protobuf(self, buffer):
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(buffer)
        return feed_response

    async def disconnect(self, close_code):
        self.keep_streaming = False
        if self.upstox_websocket:
            await self.upstox_websocket.close()
        if self.upstox_task:
            self.upstox_task.cancel()
        print("Client disconnected")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            msg = json.loads(text_data)
            if msg.get("type") == "set_instruments":
                new_instrument = msg.get("instrumentKeys")[0]
                if new_instrument and new_instrument != self.instrument_key:
                    print("Switching instrument to:", new_instrument)

                    # Close old feed immediately
                    if self.upstox_websocket:
                        await self.upstox_websocket.close()
                        self.upstox_websocket = None

                    if self.upstox_task:
                        self.upstox_task.cancel()
                        try:
                            await self.upstox_task
                        except asyncio.CancelledError:
                            pass
                        self.upstox_task = None

                    # Update current instrument
                    self.instrument_key = new_instrument

                    # Start new feed
                    self.upstox_task = asyncio.create_task(
                        self.fetch_market_data(new_instrument)
                    )

    async def fetch_market_data(self, instrument_key):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        configuration = upstox_client.Configuration()
        api_version = "3.0"
        configuration.access_token = await self.get_access_token()

        try:
            response = self.get_market_data_feed_authorize(api_version, configuration)
            url = response.data.authorized_redirect_uri

            async with websockets.connect(url, ssl=ssl_context) as websocket:
                print("Connected to Upstox WebSocket")

                await websocket.send(
                    json.dumps(
                        {
                            "guid": str(uuid.uuid4()),
                            "method": "sub",
                            "data": {
                                "mode": "full",
                                "instrumentKeys": [instrument_key],
                            },
                        }
                    ).encode("utf-8")
                )

                while self.keep_streaming:
                    try:
                        message = await websocket.recv()
                        decoded = self.decode_protobuf(message)
                        data_dict = MessageToDict(decoded)
                        data_dict = json.loads(json.dumps(data_dict))
                        ohlc = data_dict["feeds"][instrument_key]["ff"]["indexFF"][
                            "marketOHLC"
                        ]["ohlc"]
                        candle_data = [ohlc[0], ohlc[1]]
                        for elem in candle_data:
                            elem["datetime"] = int(elem["ts"]) / 1000
                            del elem["ts"]
                            del elem["interval"]
                        streaks = BrokerAppService().proccess_streak(instrument_key)
                        ce_close_list = streaks.get("CE")
                        pe_close_list = streaks.get("PE")
                        ce_trade_time = (
                            ce_close_list.get("datetime") if ce_close_list else None
                        )
                        pe_trade_time = (
                            pe_close_list.get("datetime") if pe_close_list else None
                        )

                        if streaks["CE"] and candle_data[0][
                            "close"
                        ] > ce_close_list.get("close"):
                            try:
                                await BrokerService().create_trade(
                                    strike_price=candle_data[1]["close"],
                                    option_chain_call_or_put="CE",
                                    order_type="buy",
                                    time=candle_data[1]["datetime"],
                                    buy_at=candle_data[1]["close"],
                                    target=candle_data[1]["close"] + 40,
                                    sell_at=1,
                                    trade_time=ce_trade_time,
                                )
                            except Exception as e:
                                print("Error in create trade CE:", e)
                        if streaks["PE"] and candle_data[0][
                            "close"
                        ] < pe_close_list.get("close"):
                            try:
                                await BrokerService().create_trade(
                                    strike_price=candle_data[1]["close"],
                                    option_chain_call_or_put="PE",
                                    order_type="buy",
                                    time=candle_data[1]["datetime"],
                                    buy_at=candle_data[1]["close"],
                                    target=candle_data[1]["close"] + 40,
                                    sell_at=1,
                                    trade_time=pe_trade_time,
                                )

                            except Exception as e:
                                print("Error in create trade PE:", e)
                        await self.send(
                            text_data=json.dumps(
                                {"candles": candle_data, "streaks": streaks}
                            )
                        )
                    except Exception as e:
                        print("Error in fetch loop:", e)
                        traceback.print_exc()

        except Exception as e:
            print("Upstox connection failed:", e)
            traceback.print_exc()
