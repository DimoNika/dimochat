from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

import redis
import json
from pydantic import BaseModel, constr, field_validator, Field, StringConstraints, ValidationError
from typing import Annotated
import uuid
from passlib.hash import pbkdf2_sha256
import redis.asyncio
import asyncio
import redis.asyncio.client

class UserSignup(BaseModel):
    
    username: Annotated[
        str,
        StringConstraints(
            min_length=4,
            max_length=20,
            strip_whitespace=True,
            pattern=r'^[A-Za-z0-9_]*[A-Za-z][A-Za-z0-9_]*$',  # atleast one letter
        )
    ]
    password1: Annotated[
        str,
        StringConstraints(
            min_length=4,
            max_length=24,
            strip_whitespace=True,
            pattern=r"[\w!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]+$",
        )
    ]
    password2: Annotated[
        str,
        StringConstraints(
            min_length=4,
            max_length=24,
            strip_whitespace=True,
            pattern=r"[\w!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]+$",
        )
    ]
    
    

app = FastAPI(root_path="/api/auth-service")
# redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)
redis_db = redis.asyncio.client.Redis(host="redis", port=6379, decode_responses=True)

@app.get("/")
async def main():
    print()
    return {"test": "hello worlds ale"}


@app.get("/test")
async def test():


    return {"test": "obj generated"}


from src.create_user_result import create_user_result
@app.post("/create-user")
async def create_user(request: Request, user: UserSignup):


    # user.task_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    if user.password1 == user.password2:
        data = {
        "create_user_task_id": task_id,
        "username": user.username,
        "password": pbkdf2_sha256.hash(user.password1)
        }

        json_user = json.dumps(data)

        # redis_db.("channel", "hello")

        pubsub = redis_db.pubsub()

        channel_name = f"create_user_task_id:{task_id}"

        await pubsub.subscribe(channel_name)
        await redis_db.lpush("create_user_queue", json_user)
        result = await create_user_result(pubsub, channel_name)
        # return type(result).mro

        if result["is_succesful"] == True:
            # do something cool here
            return JSONResponse(content={"data": result})
        elif result["is_succesful"] == False:
            return JSONResponse(content={"data": result}, status_code=409)
    else:
        return JSONResponse(content={"data": {"info": "Passwords don't match"}}, status_code=400)
    


    



