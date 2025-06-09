import redis

import asyncio


import redis.asyncio
import redis.asyncio.client
import json
# import redis.asyncio.client



redis_db = redis.asyncio.Redis(host="redis", port=6379, decode_responses=True)

import time

async def create_user_result(pubsub: redis.asyncio.client.PubSub, channel_name: str):
    # await pubsub.subscribe(channel_name)

    timeout = 5  # секунд
    start_time = time.monotonic()

    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
        if message:
            print(f"(Reader) Message Received: {message}", flush=True)
            print(message["data"], flush=True)
            await pubsub.unsubscribe(channel_name)
            return json.loads(message["data"])


        if time.monotonic() - start_time > timeout:
            await pubsub.unsubscribe(channel_name)
            raise Exception("No message received in 5 seconds.")

        await asyncio.sleep(0.1)