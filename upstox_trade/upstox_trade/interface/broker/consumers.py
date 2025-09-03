import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from upstox_trade.infrastructure.websocket_upstox import TickStreamService


class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.instrument_key = self.scope["url_route"]["kwargs"]["instrument_key"]

        # This is the line that needs to be correct.
        # It takes the instrument key and replaces the pipe '|' with an underscore '_'.
        self.group_name = f"trade_{self.instrument_key.replace('|', '_')}"

        # Ensure that the name is correctly formatted before calling group_add.
        print(f"Connecting to group: {self.group_name}")

        # Add this consumer to the specific group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        print(f"WebSocket connected for: {self.instrument_key}")
        await self.accept()

        # Start the tick stream service for this instrument
        self.tick_service = TickStreamService(
            instrument=self.instrument_key, use_websocket=True
        )

        # Pass the channel layer and group name to the service instance
        self.tick_service.channel_layer = self.channel_layer
        self.tick_service.group_name = self.group_name

        # Use an asyncio task to run the stream in the background
        self.stream_task = asyncio.create_task(self.tick_service.start())

    async def disconnect(self, close_code):
        print("WebSocket disconnected, stopping tick stream.")
        self.tick_service.stop()

        # Remove the consumer from the group when the client disconnects
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        # This method is for receiving messages from the client (e.g., to send a command)
        pass

    async def send_market_data(self, event):
        # This handler method is called by the channel layer
        # It sends the received message directly to the client
        await self.send(text_data=json.dumps(event["message"]))
