import os
from decouple import config
import requests
import pandas as pd
import urllib.parse

from decouple import config

from upstox_trade.domain.broker.services import BrokerService


class BrokerAppService:
    def __init__(self):
        self.broker_service = BrokerService()

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

        df["datetime"] = pd.to_datetime(df["datetime"]).astype(int) // 10**9

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

        df["datetime"] = pd.to_datetime(df["datetime"]).astype(int) // 10**9

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
