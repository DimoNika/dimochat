from fastapi import FastAPI
import redis


app = FastAPI()
redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.get("/")
async def main():
    print()
    return {"test": "hello worlds ale"}


