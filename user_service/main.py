import threading
import time
from fastapi import FastAPI
import uvicorn
import redis
import json
from contextlib import asynccontextmanager

from user_creation_worker import user_creation_worker

redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)



data = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    print("hello")
    data.append("hello ligespan")
    my_func_thread = threading.Thread(target=user_creation_worker)
    my_func_thread.start()
    
    # Если хочешь — можно подождать оба потока
    # fastapi_thread.join()
    # my_func_thread.join()
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI. User service", "data": data }

# def run_fastapi():
#     # Запускаем FastAPI на 8000 порту (uvicorn блокирует поток)
#     uvicorn.run("user_service:app", host="0.0.0.0", port=8081, reload=True)

# def queue_worker():
#     # Пример твоей функции, которая работает параллельно с сервером
#     # import logging
#     # logging.log(msg="hello log")
#     # pass
#     while True:
#         received_obj = redis_db.brpop("testqueue")[1]
        
#         obj = json.loads(received_obj)
#         data.append(received_obj)

#         print(obj["name"])
#         print(obj["age"])
        
#         print("=====================")

#         print(type(obj))



if __name__ == "__main__":
    # Создаем поток для FastAPI
    # fastapi_thread = threading.Thread(target=run_fastapi)
    # fastapi_thread.start()
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=True)
