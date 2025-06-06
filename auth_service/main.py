from fastapi import FastAPI
import redis
import json


app = FastAPI()
redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.get("/")
async def main():
    print()
    return {"test": "hello worlds ale"}


@app.get("/test")
async def main():
    print()
    obj = {
        "username": "first User",
        "password": "user_pass",
    }

    json_obj = json.dumps(obj)

    print(json_obj)
    print(type(json_obj))


    redis_db.lpush("testqueue", json_obj)
    return {"test": "obj generated"}
