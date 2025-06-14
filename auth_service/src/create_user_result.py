import redis
import asyncio
import json
import redis.asyncio.client

"""
In this file logic that receives result of user creation in user service  
"""

redis_db = redis.asyncio.Redis(host="redis", port=6379, decode_responses=True)

import time

async def create_user_result(pubsub: redis.asyncio.client.PubSub, channel_name: str):
    """
    ### This function receives result of user creation in user service.

    It iterates with `get_message()` and if succeful returns `is_succesful: True`
    if not `is_succesful: False`

    Function works 5 sec else dies
    Might be error
    """
    
    timeout = 5  # seconds
    start_time = time.monotonic()

    while True:  # Iteration and waiting for result
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
        if message:  # When gets result unsubscribes from pubsum abd returns data

            # print(f"(Reader) Message Received: {message}", flush=True)
            # print(message["data"], flush=True)
            await pubsub.unsubscribe(channel_name)
            return json.loads(message["data"])


        if time.monotonic() - start_time > timeout:  # Function works 5 sec else dies, dies here
            await pubsub.unsubscribe(channel_name)
            raise Exception("No message received in 5 seconds.")

        await asyncio.sleep(0.1)