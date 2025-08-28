import asyncio
import ssl
import json
import uuid
import websockets
from upstox_trade.domain.broker.services import MarketFeedProcessor
import redis
import requests, gzip, io, csv
from celery import shared_task
from django.utils import timezone
from .models import InstrumentDetails

r = redis.Redis(host="localhost", port=6379, db=0)


@shared_task
def fetch_and_save_upstox_instruments():
    """
    Downloads Upstox instruments .gz file, extracts in-memory,
    and saves directly into DB without writing CSV file.
    """
    url = "https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz"
    response = requests.get(url, stream=True)

    if response.status_code != 200:
        return f"❌ Failed to fetch data: {response.status_code}"

    # Decompress gzip content into memory
    compressed_file = io.BytesIO(response.content)
    with gzip.open(compressed_file, mode="rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        count = 0
        for row in reader:
            try:
                InstrumentDetails.objects.update_or_create(
                    instrument_key=row.get("instrument_key"),
                    defaults={
                        "exchange_token": row.get("exchange_token"),
                        "tradingsymbol": row.get("tradingsymbol"),
                        "name": row.get("name"),
                        "last_price": float(row.get("last_price") or 0),
                        "expiry": row.get("expiry") or "",
                        "strike": float(row.get("strike") or 0),
                        "lot_size": float(row.get("lot_size") or 0),
                        "instrument_type": row.get("instrument_type"),
                        "option_type": row.get("option_type"),
                        "modified_at": timezone.now(),
                    },
                )
                count += 1
            except Exception as e:
                print(f"❌ Error saving {row.get('instrument_key')}: {e}")

    return f"✅ {count} instruments saved/updated"


@shared_task
def upstox_live_feed():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async def fetch():
        from application.broker.service import BrokerAppService

        token = BrokerAppService().get_token(user=1)
        ws_url = "wss://..."

        async with websockets.connect(ws_url, ssl=ssl_context) as ws:
            await ws.send(
                json.dumps(
                    {
                        "guid": str(uuid.uuid4()),
                        "method": "sub",
                        "data": {
                            "mode": "full",
                            "instrumentKeys": ["NSE_INDEX|Nifty 50"],
                        },
                    }
                )
            )
            while True:
                msg = await ws.recv()
                feed_response = FeedResponse()
                feed_response.ParseFromString(msg)
                processed = MarketFeedProcessor.process(feed_response)
                r.publish("market_feed", json.dumps(processed))

    asyncio.run(fetch())
