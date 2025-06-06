from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

import redis
import json
from pydantic import BaseModel, constr, field_validator, Field, StringConstraints, ValidationError
from typing import Annotated

class UserSignup(BaseModel):
    
    username: Annotated[
        str,
        StringConstraints(
            min_length=4,
            max_length=20,
            strip_whitespace=True,
            pattern=r'^[a-zA-Z0-9_]+$',
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
redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.get("/")
async def main():
    print()
    return {"test": "hello worlds ale"}


@app.get("/test")
async def test():
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

@app.post("/create-user")
async def create_user(request: Request, user: UserSignup):
    try:
        data = await request.json()
        user = UserSignup(**data)  # ручная валидация, чтобы поймать ошибку
    except ValidationError as e:
        errors = []
        for err in e.errors():
            # err — dict с info об ошибке, например:
            # {'loc': ('field_name',), 'msg': 'error message', 'type': 'error_type'}
            errors.append({
                "field": ".".join(str(i) for i in err['loc']),
                "message": err['msg'],
                "error_type": err['type']
            })
        return JSONResponse(status_code=422, content={"errors": errors})

    user
    return {"data": user}
