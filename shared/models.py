from sqlalchemy import Column, DateTime, String, Integer, func, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base



Base = declarative_base()
metadata = Base.metadata


#  === User-service models ===

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    bio = Column(String(256))
    password = Column(String(256), nullable=False)  # hashed password

    refresh_tokens = relationship("RefreshToken", back_populates="user")
    chat_list = relationship("ChatParticipant", back_populates="user")

    def __init__(self, username, password):
        self.username = username
        self.password = password


    def __repr__(self):
        return f"Username: {self.username}, created_at: {self.created_at}"


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    id = Column(Integer, primary_key=True)
    token = Column(String(4096), nullable=False)

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User", back_populates="refresh_tokens")

    def __init__(self, token=token, user_id=user_id):
        self.token = token
        self.user_id = user_id

    def __repr__(self):
        return f"Belongs to user: {self.user}"


class ChatParticipant(Base):
    __tablename__ = "chat_participant"
    id = Column(Integer, primary_key=True)

    chat_id = Column(Integer, ForeignKey("chat.id"), nullable=False)  # chat
    chat = relationship("Chat", back_populates="participants")

    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)  # user
    user = relationship("User", back_populates="chat_list")

    joined_at = Column(DateTime, default=func.now())
    
    def __init__(self, chat_id=chat_id, user_id=user_id):
        self.chat_id = chat_id
        self.user_id = user_id


class Chat(Base):
    __tablename__ = "chat"
    id = Column(Integer, primary_key=True)
    is_group = Column(Boolean, nullable=False, default=False)
    title = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    participants = relationship("ChatParticipant", back_populates="chat")
    

class Message(Base):
    __tablename__ = "message"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chat.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    sent_at = Column(DateTime, default=func.now())
    text = Column(String(4096), nullable=False)
    is_deleted = Column(Boolean, default=False)
    edited_at = Column(DateTime, default=None)

    def __init__(self, chat_id, sender_id, text):
        self.chat_id = chat_id
        self.sender_id = sender_id
        self.text = text



