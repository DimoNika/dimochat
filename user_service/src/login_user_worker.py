import redis
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.models import User, RefreshToken
from shared.token_managment import create_refresh_token
# from ...shared.token_managment import create_refresh_token



# environment variables block
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / "shared" / ".env"
load_dotenv(env_path)


postgre_user = os.getenv("POSTGRES_USER")
postgre_password = os.getenv("POSTGRES_PASSWORD")
postgres_db = os.getenv("POSTGRES_DB")
# environment variables block



engine = create_engine(f"postgresql+psycopg2://{postgre_user}:{postgre_password}@postgres/{postgres_db}", echo=True)

Session = sessionmaker(engine)
session = Session()

"""
In this file is worker that listents to auth-service for user creating tasks

Function is syncronys
"""


redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)

class UserNotFound(Exception):
    """
    Raise when no user with specified password
    """
    pass

def login_user_worker():
    """
    This function listents for queue of user creation

    Steps:
        1. Get task and serialize it in dict
        2. Try to create user
        3. Posts to certain pubsub "is_successful": True/False
    """
    while True:

        received_obj = redis_db.brpop("login_user_queue")[1]  # listents for queue of user creation
        user: dict = json.loads(received_obj)  # serialize it in dict
        
        channel_name = f"login_user_task_id:{user['login_user_task_id']}"
        
        print(user, flush=True)
        
        try:
            # Login user
            user = session.query(User).filter_by(username=user["username"]).first()
            if user:
                token = create_refresh_token({"user_id": user.id})
                new_token = RefreshToken(token=token, user_id=user.id)
                session.add(new_token)
                session.commit()
            else:
                raise UserNotFound()



            # if session.query(User).filter(User.username == user["username"]).one_or_none():
            #     raise UsernameTaken
            
            # # Try to create user
            # new_user = User(username=user["username"], password=user["password"])
            # session.add(new_user)
            # session.commit()
            # session.refresh(new_user)
            # token = create_refresh_token({"user_id": new_user.id})
            # new_refresh_token = RefreshToken(token, new_user.id)
            # session.add(new_refresh_token)
            # session.commit()


        except UserNotFound:
            data = {
                "is_successful": False,
                "loc": "username",
                "custom_msg": "Invalid credantials"
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
                "custom_msg": "User successfuly authenticated",
                "user_id": user.id,
                "password": user.password,
                "refresh_token": token,
            }
            redis_db.publish(channel_name, json.dumps(data))

