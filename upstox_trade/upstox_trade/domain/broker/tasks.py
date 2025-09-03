import asyncio
import ssl
import json
import uuid
import websockets
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
