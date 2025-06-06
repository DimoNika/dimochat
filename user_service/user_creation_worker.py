import redis
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User
from passlib.hash import pbkdf2_sha256

engine = create_engine("postgresql+psycopg2://admin:adminpass@postgres/dimochat", echo=True)
Session = sessionmaker(engine)
session = Session()

# u = User(name="Oleg")

# session.add(u)
# session.commit()


redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)



def user_creation_worker():
    while True:

        received_obj = redis_db.brpop("testqueue")[1]
        user: dict = json.loads(received_obj)

        uname = user.get("username")
        upass = user.get("password")
        new_user = User(username=uname, password=upass)
        
        session.add(new_user)
        session.commit()


        
        print("=====================")

        