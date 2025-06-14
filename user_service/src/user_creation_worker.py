import redis
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User


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
        3. Posts to certain pubsub "is_succesful": True/False
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

        except UsernameTaken:
            data = {
                "is_succesful": False,
                "loc": "username",
                "custom_msg": "Username already taken"
            }
            redis_db.publish(channel_name, json.dumps(data))

        except Exception as e:
            data = {
                "is_succesful": False,
                "custom_msg": "Unknown error occured",
            }
            redis_db.publish(channel_name, json.dumps(data))

        else:
            data = {
                "is_succesful": True,
                "custom_msg": "User succefuly created"
            }
            redis_db.publish(channel_name, json.dumps(data))

