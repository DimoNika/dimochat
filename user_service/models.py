from sqlalchemy import Column, DateTime, String, Integer, func, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base



UserServiceBase = declarative_base()
metadata = UserServiceBase.metadata


#  === User-service models ===

class User(UserServiceBase):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    bio = Column(String(256))
    password = Column(String(256), nullable=False)  # hashed password

    refresh_tokens = relationship("RefreshToken", back_populates="user")

    def __init__(self, username, password):
        self.username = username
        self.password = password


    def __repr__(self):
        return f"Username: {self.username}, created_at: {self.created_at}"

class RefreshToken(UserServiceBase):
    __tablename__ = "refresh_token"
    id = Column(Integer, primary_key=True)
    token = Column(String(4096), nullable=False)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User", back_populates="refresh_tokens")

    def __init__(self, token=token, user_id=user_id):
        self.token = token
        self.user_id = user_id

