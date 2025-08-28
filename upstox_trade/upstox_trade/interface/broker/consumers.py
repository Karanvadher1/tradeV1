# import asyncio
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# import aioredis


# class UpstoxConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         await self.accept()
#         self.redis = await aioredis.from_url("redis://localhost:6379")
#         asyncio.create_task(self.stream_data())

#     async def disconnect(self, close_code):
#         await self.redis.close()

#     async def stream_data(self):
#         pubsub = self.redis.pubsub()
#         await pubsub.subscribe("market_feed")

#         async for message in pubsub.listen():
#             if message["type"] == "message":
#                 await self.send(text_data=message["data"].decode())
