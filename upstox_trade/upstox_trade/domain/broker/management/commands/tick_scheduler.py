import asyncio
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from django.core.management import BaseCommand
from channels.layers import get_channel_layer
from upstox_trade.infrastructure.websocket_upstox import TickStreamService

# Create a global service instance
tick_service_instance = TickStreamService(
    instrument="NSE_INDEX|Nifty 50", use_websocket=True
)

# Connect the service instance to the channel layer
tick_service_instance.channel_layer = get_channel_layer()
# Set the group name here, making it accessible globally
tick_service_instance.group_name = "trade_NSE_INDEX_Nifty_50"


class Command(BaseCommand):
    help = "Run Upstox websocket between 9:00 and 15:45"

    def handle(self, *args, **options):
        loop = asyncio.get_event_loop()
        scheduler = AsyncIOScheduler(event_loop=loop)

        @scheduler.scheduled_job("cron", day_of_week="mon-fri", hour=9, minute=0)
        async def start_ticks():
            msg = f"{'=' * 50} Starting tick stream at 09:00... {'=' * 50}"
            self.stdout.write(self.style.SUCCESS(msg))
            asyncio.create_task(tick_service_instance.start())

        @scheduler.scheduled_job("cron", day_of_week="mon-fri", hour=16, minute=45)
        async def stop_ticks():
            msg = f"{'=' * 50} Stopping tick stream at 15:45... {'=' * 50}"
            self.stdout.write(self.style.WARNING(msg))
            tick_service_instance.stop()

        scheduler.start()

        now = datetime.now().time()
        if time(9, 0) <= now < time(16, 45):
            msg = f"{'=' * 50} Market already open ({now}), starting immediately... {'=' * 50}"
            self.stdout.write(self.style.SUCCESS(msg))
            loop.create_task(tick_service_instance.start())

        self.stdout.write(
            self.style.SUCCESS(f"{'=' * 50} Scheduler running... {'=' * 50}")
        )

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            scheduler.shutdown()
            self.stdout.write(
                self.style.WARNING(f"{'=' * 50} Scheduler stopped manually {'=' * 50}")
            )
