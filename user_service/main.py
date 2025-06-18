import threading
import time
from fastapi import FastAPI
import uvicorn
import redis
import json
from contextlib import asynccontextmanager

from src.user_creation_worker import user_creation_worker
from src.login_user_worker import login_user_worker


redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)


# This function launches before fastapi instace runes
@asynccontextmanager
async def lifespan(app: FastAPI):

    # Creating thread with function that waits user creation request fron autrh service
    my_func1_thread = threading.Thread(target=user_creation_worker)
    my_func1_thread.start()
    my_func1_thread = threading.Thread(target=login_user_worker)
    my_func1_thread.start()
    yield

app = FastAPI(lifespan=lifespan, root_path="/api/user-service")  # Fastapi app initialization with its user-service default path


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8081, reload=True)
