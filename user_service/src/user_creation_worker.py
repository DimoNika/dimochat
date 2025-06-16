import redis
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, RefreshToken
from .token_managment import create_refresh_token


engine = create_engine("postgresql+psycopg2://admin:adminpass@postgres/dimochat", echo=True)
Session = sessionmaker(engine)
session = Session()

"""
In this file is worker that listents to auth-service for user creating tasks

Function is suncronys
"""


redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)

class UsernameTaken(Exception):
    """
    Raise when username taken
    """
    pass

def user_creation_worker():
    """
    This function listents for queue of user creation

    Steps:
        1. Get task and serialize it in dict
        2. Try to create user
        3. Posts to certain pubsub "is_successful": True/False
    """
    while True:

        received_obj = redis_db.brpop("create_user_queue")[1]  # listents for queue of user creation
        user: dict = json.loads(received_obj)  # serialize it in dict
        
        channel_name = f"create_user_task_id:{user['create_user_task_id']}"
        
        
        try:
            if session.query(User).filter(User.username == user["username"]).one_or_none():
                raise UsernameTaken
            
            # Try to create user
            new_user = User(username=user["username"], password=user["password"])
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            token = create_refresh_token({"user_id": new_user.id})
            new_refresh_token = RefreshToken(token, new_user.id)
            session.add(new_refresh_token)
            session.commit()


        except UsernameTaken:
            data = {
                "is_successful": False,
                "loc": "username",
                "custom_msg": "Username already taken"
            }
            redis_db.publish(channel_name, json.dumps(data))

        except Exception as e:
            data = {
                "is_successful": False,
                "custom_msg": "Unknown error occured",
            }
            print(str(e), flush=True)
            redis_db.publish(channel_name, json.dumps(data))

        else:
            data = {
                "is_successful": True,
                "custom_msg": "User successfuly created",
                "user_id": new_user.id,
                "refresh_token": token
            }
            redis_db.publish(channel_name, json.dumps(data))

