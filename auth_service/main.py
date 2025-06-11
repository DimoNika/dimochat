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
async def create_user(request: Request):

    try:
        body = await request.json()
        user = UserSignup(**body)  # вручную вызываем валидацию
        print(type(user), "asdjapsjdjlk")
    except ValidationError as validation_error:
        validation_error : ValidationError
        
        result_response = []
        for error in validation_error.errors():
            error_info = {
                "loc": error["loc"][0]
            }
            # too long
            if error["type"] == "string_too_long":
                error_info["custom_msg"] = "Too long."
            # too short
            elif error["type"] == "string_too_short":
                error_info["custom_msg"] = "Too short."
            # too pattern mismatch
            elif error["type"] == "string_too_short":
                error_info["custom_msg"] = "Forbidden symbols."
            # else
            else:
                error_info["custom_msg"] = "Unknown error."
            result_response.append(error_info)
        return JSONResponse(content=result_response, status_code=409)


                

            

#   {
#     "type": "string_too_short",
#     "loc": [
#       "username"
#     ],
#     "msg": "String should have at least 4 characters",
#     "input": "a!",
#     "ctx": {
#       "min_length": 4
#     },
#     "url": "https://errors.pydantic.dev/2.11/v/string_too_short"
#   },
        return
        # user = UserSignup(**body)  # вручную вызываем валидацию


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
            return JSONResponse(content=[result])
        elif result["is_succesful"] == False:
            return JSONResponse(content=[result], status_code=409)
    else:
        return JSONResponse(content=[{"custom_msg": "Passwords don't match"}], status_code=400)
    


    



