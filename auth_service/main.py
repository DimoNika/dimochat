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
# from src.token_managment import create_access_token, create_refresh_token, decode, auth
from shared.token_managment import create_access_token, create_refresh_token, decode, auth
from src.pubsub_response_getter import listen_pubsub_result
# from src.create_user_rt_result import create_rt_user_result
# from src.login_user_result import login_user_result

# from src.token_managment import 



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
    
class UserLogin(BaseModel):
    
    username: Annotated[str, StringConstraints()]
    password: Annotated[str, StringConstraints()]


app = FastAPI(root_path="/api/auth-service")  # Fastapi app initialization with its auth-service default path
redis_db = redis.asyncio.client.Redis(host="redis", port=6379, decode_responses=True)  # redis_db instance initialization



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

    2. If serialized successfully passes data to user-service.
    
    Steps:
        a. Create data.
        b. Start to listen pubsub about result of user creation.
        c. Then pass data to user-serivice.
        d. Handle result.

    Functions returns:
        `JsonRespose`s with respective status_code`s
        `List[Dict[str, str]]`
        {
            "is_successful": bool,
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
                "is_successful": False,
                "loc": error["loc"][0]  # mark for frontend in which field error occured. Very important
            }
            # too long
            if error["type"] == "string_too_long":
                error_info["custom_msg"] = "Too long."
            # too short
            elif error["type"] == "string_too_short":
                error_info["custom_msg"] = "Too short."
            # too pattern mismatch
            elif error["type"] == "string_pattern_mismatch":
                error_info["custom_msg"] = "Forbidden symbols."
            # else
            else:
                error_info["custom_msg"] = "Unknown error."
            result_response.append(error_info)
        return JSONResponse(content=result_response, status_code=409)  # in case of serialization error return to client


    # 2. If serialized successfully passes data to user-service.
    task_id = str(uuid.uuid4())
    if user.password1 == user.password2:
        # Data which which pass to user-service
        # refresh_token = create_refresh_token(data)
        data = {
            "create_user_task_id": task_id,
            "username": user.username,
            "password": pbkdf2_sha256.hash(user.password1),

        }
        # Serialize data to JSON string type
        json_user = json.dumps(data)


        pubsub = redis_db.pubsub()  # Initialize pubsub object
        channel_name = f"create_user_task_id:{task_id}"  # Initialize channel name

        await pubsub.subscribe(channel_name)  # Subscribe to channel
        await redis_db.lpush("create_user_queue", json_user)  # Pass data to user-service

        try:
            result: dict = await listen_pubsub_result(pubsub, channel_name)  # Receive result about user creation
        except Exception:
            # If in create_user_result() error occured
            JSONResponse(content=[{  
                "is_successful": False,
                "custom_msg": "Unknow result of usercreation in user-service"
            }], status_code=500)
        
        # Handle result
        if result["is_successful"] == True:
            """
            Access-token we send in response and Refresh-token we send as Cookie
            """

            token_data = {
                "user_id": result["user_id"]
            }

            access_token = create_access_token(token_data)
            
            result.update({"access_token": access_token})

            #  Set-Cookie in response
            response = JSONResponse(content=result)
            response.set_cookie(
                key="refresh_token",
                value=result["refresh_token"],
                httponly=True,
                max_age=4_320_000,
                samesite="Strict",
                secure=True
            )
            
            return response
        elif result["is_successful"] == False:
            return JSONResponse(content=[result], status_code=409)
    else:
        return JSONResponse(content=[{"custom_msg": "Passwords don't match"}], status_code=400)
    

@app.post("/refresh")
async def refresh(request: Request):
    print(request.cookies)

    try:
        token = request.cookies.get("refresh_token") 
        if token:  # If there is no token return unauthenticated
            if auth(token):
                token_data = decode(token)

                # Data to encode to access token
                access_token_data =  {
                    "user_id": token_data["user_id"]
                }

                # Data that will be returned to the client
                data = {
                    "access_token": create_access_token(access_token_data)
                }
                return data
            else:
                return JSONResponse(content={"custom_msg": "Refresh token unauthenticated"}, status_code=401)
            

        else: # If there is no token return unauthenticated
            return JSONResponse(content={"custom_msg": "No refresh token provided"}, status_code=401)
    except Exception as e:
        return JSONResponse(content={"custom_msg": f"Unknown error occured during access token refreshing: {str(e)}", "loc": "/api/auth-service/refresh"}, status_code=401)
    

    
    # # return "alo"
    # try:
    #     request.cookies["refresh_token"]
    # except ValueError:
    #     return JSONResponse(content={"custom_msg": "No refresh token provided"}, status_code=401)
    
    # if not request.cookies["refresh_token"][1]:
    #     return JSONResponse(content={"custom_msg": "No refresh token provided"}, status_code=401)


    # if auth(request.cookies["refresh_token"]):
    #     refresh_token = decode(request.cookies["refresh_token"])
    #     access_token_data =  {
    #         "user_id": refresh_token["user_id"]
    #     }

    #     data = {
    #         "access_token": create_access_token(access_token_data)
    #     }
    #     return data
    # else:
    #     return JSONResponse(status_code=401)

@app.post("/login")
async def refresh(request: Request, user: UserLogin):

    task_id = str(uuid.uuid4())
    # Data which which pass to user-service
    data = {
        "login_user_task_id": task_id,
        "username": user.username,
        # "password": pbkdf2_sha256.hash(user.password),
    }
    # Serialize data to JSON string type
    json_user = json.dumps(data)


    pubsub = redis_db.pubsub()  # Initialize pubsub object
    channel_name = f"login_user_task_id:{task_id}"  # Initialize channel name

    await pubsub.subscribe(channel_name)  # Subscribe to channel
    await redis_db.lpush("login_user_queue", json_user)  # Pass data to user-service

    # try:

    result: dict = await listen_pubsub_result(pubsub, channel_name)  # Receive result about user creation
    if result["is_successful"] == True:
        if pbkdf2_sha256.verify(user.password, result["password"]):
            response_data = {
            "is_successful": True
            }

            token_data = {
                "user_id": result["user_id"]
            }
            access_token = create_access_token(token_data)
            response_data.update({"access_token": access_token})

            response = JSONResponse(content=response_data)

            response.set_cookie(
                key="refresh_token",
                value=result["refresh_token"],
                httponly=True,
                max_age=4_320_000,
                samesite="Strict",
                secure=True
            )



            return response
        else:
            return JSONResponse(content={"custom_msg": "Unsuccessful to find user."}, status_code=500)
            
    else:
        response_data = {
            "is_successful": False,
            "custom_msg": "Invalid credentials"
        }
        return JSONResponse(content=response_data, status_code=401)



@app.get("/auth")
async def auth_user(request: Request):
    authenticate_header: str = request.headers.get("Authenticate")
    print(authenticate_header)
    if authenticate_header:
        authenticate_header_parts = authenticate_header.split(" ")
        if authenticate_header_parts[0] == "Bearer":
            return auth(authenticate_header_parts[1])  # Returns true or false
        else: 
            return JSONResponse(content={"custom_msg": "Some headers problems"}, status_code=400)
    else:
        return JSONResponse(content={"custom_msg": "No header provided"}, status_code=400)



@app.get("/logout")
async def logout():
    response = JSONResponse(content={"detail": "User logged out."})
    response.set_cookie(
        key="refresh_token",
        value={},
        httponly=True,
        max_age=1,
        samesite="Strict",
        secure=True
    )
    return response
