from collections import defaultdict
import os
from decouple import config
import requests
import pandas as pd
import urllib.parse

from decouple import config

from upstox_trade.domain.broker.services import BrokerService, IntradayService


class BrokerAppService:
    def __init__(self):
        self.broker_service = BrokerService()
        self.intraday_service = IntradayService()

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

    def get_instrument_data(self, instrument_key, interval, unit):
        instrument_key_encoded = urllib.parse.quote(instrument_key, safe="")
        file_name = f"{instrument_key}.csv"

        # Check if the file exists and delete it
        if os.path.exists(file_name):
            os.remove(file_name)
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

        df.to_csv(instrument_key, index=False)
        return df.to_dict(orient="records")

    def proccess_streak(self, instrument_key):
        df = pd.read_csv(instrument_key)
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
                selected_candle = df.loc[min_low_idx]
                streaks["PE"] = selected_candle.to_dict()

            # RED streak leogic
            elif group_df["candle_color"].iloc[0] == "red":
                max_high_idx = group_df["high"].idxmax()
                selected_candle = df.loc[max_high_idx]
                streaks["CE"] = selected_candle.to_dict()
        return streaks

    def get_index_details(self):
        return self.broker_service.get_index_details()

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

    def build_candles(ticks, interval_minutes=1):
        """
        ticks: list of dicts with 'datetime' and 'close'
        interval_minutes: candle size (1, 3, 5, 15, ...)
        """
        candles = []
        grouped = defaultdict(list)

        for tick in ticks:
            dt = tick["datetime"].replace(
                second=0, microsecond=0
            )  # round to nearest min
            # align to interval start
            minute_block = dt.minute - (dt.minute % interval_minutes)
            interval_start = dt.replace(minute=minute_block, second=0, microsecond=0)

            grouped[interval_start].append(tick)

        for interval_start, group in sorted(grouped.items()):
            opens = group[0]["open"]
            closes = group[-1]["close"]
            highs = max(t["high"] for t in group)
            lows = min(t["low"] for t in group)

            candles.append(
                {
                    "datetime": interval_start,
                    "open": opens,
                    "high": highs,
                    "low": lows,
                    "close": closes,
                }
            )

        return candles
