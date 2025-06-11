import redis
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User


engine = create_engine("postgresql+psycopg2://admin:adminpass@postgres/dimochat", echo=True)
Session = sessionmaker(engine)
session = Session()

# u = User(name="Oleg")

# session.add(u)
# session.commit()


redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)
redis_db.publish("test_channel", "hello")

class UsernameTaken(Exception):
    """
    Raise when username taken
    """
    pass

def user_creation_worker():
    while True:

        received_obj = redis_db.brpop("create_user_queue")[1]
        user: dict = json.loads(received_obj)
        print(user, flush=True)
        channel_name = f"create_user_task_id:{user['create_user_task_id']}"
        
        
        try:
            if session.query(User).filter(User.username == user["username"]).one_or_none():
                print("user exists", flush=True)
                raise UsernameTaken
            
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
                "test": str(e)
            }
            redis_db.publish(channel_name, json.dumps(data))

        else:
            data = {
                "is_succesful": True,
                "info": "User succefuly created"
            }
            redis_db.publish(channel_name, json.dumps(data))
