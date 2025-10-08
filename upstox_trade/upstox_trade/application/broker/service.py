from datetime import datetime, time
import math
import os
from decouple import config
import numpy as np
import requests
import pandas as pd
import urllib.parse
from asgiref.sync import sync_to_async

import traceback
import sys
from decouple import config

from upstox_trade.domain.broker.services import (
    BrokerService,
    InstrumentService,
    IntradayService,
)
from upstox_trade.application.notification.services import NotificationAppService


class BrokerAppService:
    def __init__(self):
        self.broker_service = BrokerService()
        self.intraday_service = IntradayService()
        self.instrument_service = InstrumentService()

    def login(self):
        pass

    def create_strategy(self, name, support, resistance):
        return self.broker_service.create_strategy(name, support, resistance)

    def get_strategy_by_name(self, name):
        return self.broker_service.get_strategy_by_name(name=name)

    def save_token(self, token: dict, user: str):
        return self.broker_service.save_token(token, user)

    def get_token(self, user: str):
        token_obj = self.broker_service.get_token(user)
        return str(token_obj.access_token)

    def create_trade(
        self,
        strike_price,
        option_chain_call_or_put,
        order_type,
        time,
        buy_at,
        target,
        sell_at,
        chart="NSE_INDEX|Nifty 50",
    ):
        strategy = self.broker_service.get_strategy_by_name("swing")
        return self.broker_service.create_trade(
            strategy,
            chart,
            strike_price,
            option_chain_call_or_put,
            order_type,
            time,
            buy_at,
            target,
            sell_at,
        )

    def get_instrument_historical_data(
        self, instrument_key, interval, unit, from_date, to_date
    ):
        instrument_key_encoded = urllib.parse.quote(instrument_key, safe="")
        base_url = config("HISTORICAL_DATA_URL")
        url = f"{base_url}/{instrument_key_encoded}/{unit}/{interval}/{to_date}/{from_date}/"

        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers)
        data = response.json()["data"]["candles"]

        df = pd.DataFrame(
            data,
            columns=["datetime", "open", "high", "low", "close", "volume", "other"],
        )
        df = df.loc[:, ["datetime", "open", "high", "low", "close"]]

        df["datetime"] = pd.to_datetime(df["datetime"]).dt.floor("min")

        return df.to_dict(orient="records")

    def get_instrument_intraday_data(self, instrument_key, interval, unit):
        instrument_key_encoded = urllib.parse.quote(instrument_key, safe="")
        safe_instrument_key = instrument_key.replace("|", "_").replace(" ", "_")

        file_name = f"{safe_instrument_key}_{datetime.now().date()}.csv"
        # Check if the file exists and delete it
        # if os.path.exists(file_name):
        #     os.remove(file_name)
        base_url = config("INTRADAY_DATA_URL")
        payload = {}
        url = f"{base_url}/{instrument_key_encoded}/{unit}/{interval}/"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, data=payload)
        data = response.json()["data"]["candles"]
        df = pd.DataFrame(
            data,
            columns=["datetime", "open", "high", "low", "close", "volume", "other"],
        )
        df = df.loc[:, ["datetime", "open", "high", "low", "close"]]

        df["datetime"] = pd.to_datetime(df["datetime"]).dt.floor("min")

        df.to_csv(file_name, index=False)
        return df.to_dict(orient="records")

    async def get_option_intraday_data(self, instrument_key):

        instrument_key_encoded = urllib.parse.quote(instrument_key, safe="")
        unit = "minutes"
        interval = "1"
        current_time = datetime.now().time()
        if current_time >= time(10, 30):
            interval = "3"
        base_url = config("INTRADAY_DATA_URL")
        payload = {}
        url = f"{base_url}/{instrument_key_encoded}/{unit}/{interval}/"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, data=payload)
        data = response.json()["data"]["candles"]
        df = pd.DataFrame(
            data,
            columns=["datetime", "open", "high", "low", "close", "volume", "other"],
        )
        df = df.loc[:, ["datetime", "open", "high", "low", "close"]]

        df["datetime"] = pd.to_datetime(df["datetime"]).dt.floor("min")
        return df

    async def proccess_streak(self, instrument_key, start_time=None, end_time=None):
        safe_instrument_key = instrument_key.replace("|", "_").replace(" ", "_")

        file_name = f"{safe_instrument_key}_{datetime.now().date()}.csv"
        if os.path.exists(file_name):
            df = pd.read_csv(file_name)
            df = df.iloc[::-1].reset_index(drop=True)
            df["candle_color"] = df.apply(
                lambda row: "green" if row["open"] < row["close"] else "red", axis=1
            )
            df["group"] = (df["candle_color"] != df["candle_color"].shift()).cumsum()

            streaks = {"CE": {}, "PE": {}}
            for group, group_df in df.groupby("group"):
                if len(group_df) < 3:
                    continue

                # GREEN streak logic
                if group_df["candle_color"].iloc[0] == "green":
                    min_low_idx = group_df["low"].idxmin()
                    selected_candle = df.loc[min_low_idx].to_dict()
                    selected_candle["start_time"] = group_df.iloc[0]["datetime"]
                    selected_candle["end_time"] = group_df.iloc[-1]["datetime"]
                    streaks["PE"] = selected_candle

                # RED streak leogic
                elif group_df["candle_color"].iloc[0] == "red":
                    max_high_idx = group_df["high"].idxmax()
                    selected_candle = df.loc[max_high_idx].to_dict()
                    selected_candle["start_time"] = group_df.iloc[0]["datetime"]
                    selected_candle["end_time"] = group_df.iloc[-1]["datetime"]
                    streaks["CE"] = selected_candle

            return streaks
        else:
            df = await self.get_option_intraday_data(instrument_key=instrument_key)
            filtered_df = df[
                (df["datetime"] >= start_time) & (df["datetime"] <= end_time)
            ]
            filtered_df = filtered_df.iloc[::-1].reset_index(drop=True)
            filtered_df["candle_color"] = filtered_df.apply(
                lambda row: "green" if row["open"] < row["close"] else "red", axis=1
            )
            filtered_df["group"] = (
                filtered_df["candle_color"] != filtered_df["candle_color"].shift()
            ).cumsum()

            streak = {}
            for group, group_df in filtered_df.groupby("group"):
                if len(group_df) < 3:
                    continue

                # GREEN streak logic
                if group_df["candle_color"].iloc[0] == "green":
                    min_low_idx = group_df["low"].idxmin()
                    selected_candle = filtered_df.loc[min_low_idx].to_dict()
                    selected_candle["start_time"] = group_df.iloc[0]["datetime"]
                    selected_candle["end_time"] = group_df.iloc[-1]["datetime"]
                    streak = selected_candle

                # RED streak leogic
                elif group_df["candle_color"].iloc[0] == "red":
                    max_high_idx = group_df["high"].idxmax()
                    selected_candle = filtered_df.loc[max_high_idx].to_dict()
                    selected_candle["start_time"] = group_df.iloc[0]["datetime"]
                    selected_candle["end_time"] = group_df.iloc[-1]["datetime"]
                    streak = selected_candle

            return streak

    def get_intraday_data(self, instrument_key, interval):
        qs = (
            self.intraday_service.get_intraday_data(instrument_key)
            .order_by("-created_at")[:2]
            .values("datetime", "open", "high", "low", "close")
        )

        df = pd.DataFrame.from_records(qs)
        df.set_index("datetime", inplace=True)

        candles = (
            df.resample(interval)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                }
            )
            .dropna()
            .reset_index()
        )

        return candles.to_dict(orient="records")

    # def build_candles(ticks, interval_minutes=1):
    #     """
    #     ticks: list of dicts with 'datetime' and 'close'
    #     interval_minutes: candle size (1, 3, 5, 15, ...)
    #     """
    #     candles = []
    #     grouped = defaultdict(list)

    #     for tick in ticks:
    #         dt = tick["datetime"].replace(
    #             second=0, microsecond=0
    #         )  # round to nearest min
    #         # align to interval start
    #         minute_block = dt.minute - (dt.minute % interval_minutes)
    #         interval_start = dt.replace(minute=minute_block, second=0, microsecond=0)

    #         grouped[interval_start].append(tick)

    #     for interval_start, group in sorted(grouped.items()):
    #         opens = group[0]["open"]
    #         closes = group[-1]["close"]
    #         highs = max(t["high"] for t in group)
    #         lows = min(t["low"] for t in group)

    #         candles.append(
    #             {
    #                 "datetime": interval_start,
    #                 "open": opens,
    #                 "high": highs,
    #                 "low": lows,
    #                 "close": closes,
    #             }
    #         )

    #     return candles


class InstrumentAppService:
    def __init__(self):
        self.instrument_service = InstrumentService()

    def get_index_details(self, symbol=None):
        return self.instrument_service.get_index_details(symbol=symbol)


class StretagyAppService:
    def __init__(self):
        self.broker_app_service = BrokerAppService()
        self.broker_service = BrokerAppService()
        self.notification_app_service = NotificationAppService()
        self.instrument_service = InstrumentService()

    async def get_call_strikes(self, spot, step=50, count=1):
        lower_bound = math.floor(spot / step - count) * step
        upper_bound = math.ceil(spot / step) * step
        base = np.arange(lower_bound, upper_bound + step, step)
        return int(base[base <= spot][-1])

    async def get_put_strikes(self, spot, step=50, count=1):
        spot = float(spot)
        lower_bound = math.floor(spot / step) * step
        upper_bound = math.ceil(spot / step + count) * step
        base = np.arange(lower_bound, upper_bound + step, step)
        return int(base[base >= spot][0]) if len(base[base >= spot]) else None

    async def calculate_trade(self, instrument_key, candle):
        try:
            current_time = datetime.now().time()
            # get last candle of 3 candle
            if current_time > time(10, 30):
                safe_instrument_key = instrument_key.replace("|", "_").replace(" ", "_")
                file_name = f"{safe_instrument_key}_{datetime.now().date()}.csv"
                df = pd.read_csv(file_name)
                candle = df.iloc[0].to_dict()

            index_streaks = await self.broker_service.proccess_streak(instrument_key)
            candle_close = candle["close"]
            if index_streaks["CE"] and candle_close:
                call_strike = await self.get_call_strikes(float(candle_close))
                instrument = await sync_to_async(
                    self.instrument_service.get_option_chain_by_strike
                )(strike=call_strike, option_type="CE")
                option_streaks = await self.broker_service.proccess_streak(
                    instrument_key=instrument.instrument_key,
                    start_time=index_streaks["CE"]["start_time"],
                    end_time=index_streaks["CE"]["end_time"],
                )
                if option_streaks:
                    ce_trade_time = index_streaks["CE"]["datetime"]

                    if candle_close > index_streaks["CE"]["close"]:
                        try:
                            trade = await BrokerService().create_trade(
                                strike_price=candle_close,
                                option_chain_call_or_put="CE",
                                order_type="buy",
                                time=candle["datetime"],
                                buy_at=candle_close,
                                target=candle_close + 40,
                                sell_at=1,
                                trade_time=ce_trade_time,
                            )
                            if trade is not None:
                                print("*" * 100, "Trade created", "*" * 100)
                                notification_instance = await sync_to_async(
                                    self.notification_app_service.create_notification
                                )(
                                    {
                                        "notification_type": "trade",
                                        "content": "Trade Created",
                                        "instrument": instrument,
                                        "trade": trade,
                                        "price": candle_close,
                                        "related_url": "https://upstox.com",
                                    }
                                )

                        except Exception as e:
                            print("Error in create trade CE:", e)

            if index_streaks["PE"] and candle_close:
                put_strike = await self.get_put_strikes(float(candle_close))
                instrument = await sync_to_async(
                    self.instrument_service.get_option_chain_by_strike
                )(put_strike, "PE")
                option_streaks = await self.broker_service.proccess_streak(
                    instrument_key=instrument.instrument_key,
                    start_time=index_streaks["PE"]["start_time"],
                    end_time=index_streaks["PE"]["end_time"],
                )
                pe_trade_time = index_streaks["PE"]["datetime"]

                if candle_close < index_streaks["PE"]["close"]:
                    try:
                        trade = await BrokerService().create_trade(
                            strike_price=instrument.instrument_key,
                            option_chain_call_or_put="PE",
                            order_type="buy",
                            time=candle["datetime"],
                            buy_at=candle_close,
                            target=candle_close + 40,
                            sell_at=1,
                            trade_time=pe_trade_time,
                        )

                        if trade is not None:
                            print("*" * 100, "Trade created", "*" * 100)
                            notification_instance = await sync_to_async(
                                self.notification_app_service.create_notification
                            )(
                                {
                                    "notification_type": "trade",
                                    "content": "Trade Created",
                                    "instrument": instrument,
                                    "trade": trade,
                                    "price": candle_close,
                                    "related_url": "",
                                }
                            )
                    except Exception as e:
                        print("Error in create trade PE:", e)
        except Exception as e:
            # Capture the traceback
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb = traceback.extract_tb(exc_tb)

            # Last call in the traceback is where the error occurred
            filename, lineno, func, text = tb[-1]
            print(f"❌ Error in calculate_trade: {e}")
            print(f"   → File: {filename}, Line: {lineno}, in {func}")
            print(f"   → Code: {text}")
