
import redis
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.models import User, RefreshToken, ChatParticipant
from sqlalchemy import select



engine = create_engine("postgresql+psycopg2://admin:adminpass@localhost/dimochat", echo=True)
Session = sessionmaker(engine)
session = Session()

# session.
result = session.query(User).filter_by(id=69).first()
print(result.refresh_tokens)



# result = session.select(RefreshToken).order_by(User.id)

# for row in result:
#     try:
#         print(row)
#     except UnicodeDecodeError as e:
#         print("Ошибка при выводе строки:", str(e))
# for user_obj in result.scalars():
#     print(user_obj)
#     print(f"{user_obj}")
