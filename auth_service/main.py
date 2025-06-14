from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

import redis
import json
from pydantic import BaseModel, StringConstraints, ValidationError
from typing import Annotated
import uuid
from passlib.hash import pbkdf2_sha256
import redis.asyncio.client



# Serialization model declaration
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
    
    

app = FastAPI(root_path="/api/auth-service")  # Fastapi app initialization with its auth-service default path
redis_db = redis.asyncio.client.Redis(host="redis", port=6379, decode_responses=True)  # redis_db instance initialization


from src.create_user_result import create_user_result
@app.post("/create-user")
async def create_user(request: Request):
    """
    #### This func gets user in body and parses it in `UserSignup` model then sends
    #### task to user-service to create user in DB, gets result of this task and
    #### returns to client.

    Steps:
    1. Serialize body to `UserSignup`, if errors occur hadles and returns to client.

    Error types:
        a. Field too short.
        b. Field too long.
        c. Pattern mismatch.

    2. If serialized succesfully passes data to user-service.
    
    Steps:
        a. Create data.
        b. Start to listen pubsub about result of user creation.
        c. Then pass data to user-serivice.
        d. Handle result.

    Functions returns:
        `JsonRespose`s with respective status_code`s
        `List[Dict[str, str]]`
        {
            "is_succesful": bool,
            "loc": str,
            custom_msg: str
        }
                
    """

    # 1. Serialize body to `UserSignup`, if errors occur hadles and returns to client.
    try:
        body = await request.json()
        user = UserSignup(**body)  # Serialize manulally
    except ValidationError as validation_error:
        validation_error : ValidationError

        result_response = []
        for error in validation_error.errors():  # iterate in errors list
            error_info = {
                "is_succesful": False,
                "loc": error["loc"][0]  # mark for frontend in which field error occured. Very important
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
        return JSONResponse(content=result_response, status_code=409)  # in case of serialization error return to client


    # 2. If serialized succesfully passes data to user-service.
    task_id = str(uuid.uuid4())
    if user.password1 == user.password2:
        # Data which which pass to user-service
        data = {
            "create_user_task_id": task_id,
            "username": user.username,
            "password": pbkdf2_sha256.hash(user.password1)
        }
        # Serialize data to JSON string type
        json_user = json.dumps(data)


        pubsub = redis_db.pubsub()  # Initialize pubsub object
        channel_name = f"create_user_task_id:{task_id}"  # Initialize channel name

        await pubsub.subscribe(channel_name)  # Subscribe to channel
        await redis_db.lpush("create_user_queue", json_user)  # Pass data to user-service
        try:
            result = await create_user_result(pubsub, channel_name)  # Receive result about user creation
        except Exception:
            # If in create_user_result() error occured
            JSONResponse(content=[{  
                "is_succesful": False,
                "custom_msg": "Unknow result of usercreation in user-service"
            }], status_code=500)
        
        # Handle result
        if result["is_succesful"] == True:
            # do something cool here
            return JSONResponse(content=[result])
        elif result["is_succesful"] == False:
            return JSONResponse(content=[result], status_code=409)
    else:
        return JSONResponse(content=[{"custom_msg": "Passwords don't match"}], status_code=400)
    
