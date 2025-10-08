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
    deletes existing InstrumentDetails, and bulk creates all new ones.
    """
    url = "https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz"
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        return f"❌ Failed to fetch data: {response.status_code}"

    # Decompress gzip content into memory
    compressed_file = io.BytesIO(response.content)
    with gzip.open(compressed_file, mode="rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        instruments = []
        now = timezone.now()

        for row in reader:
            try:
                instruments.append(
                    InstrumentDetails(
                        instrument_key=row.get("instrument_key"),
                        exchange_token=row.get("exchange_token"),
                        tradingsymbol=row.get("tradingsymbol"),
                        name=row.get("name"),
                        last_price=float(row.get("last_price") or 0),
                        expiry=row.get("expiry") or "",
                        strike=float(row.get("strike") or 0),
                        lot_size=float(row.get("lot_size") or 0),
                        instrument_type=row.get("instrument_type"),
                        option_type=row.get("option_type"),
                        modified_at=now,
                    )
                )
            except Exception as e:
                print(f"❌ Error parsing {row.get('instrument_key')}: {e}")

    # Delete old data
    InstrumentDetails.objects.all().delete()

    # Bulk insert
    InstrumentDetails.objects.bulk_create(instruments, batch_size=5000)

    return f"✅ {len(instruments)} instruments inserted"
