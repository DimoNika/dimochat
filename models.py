from sqlalchemy import Column, DateTime, String, Integer, func
from sqlalchemy.ext.declarative import declarative_base



Base = declarative_base()
metadata = Base.metadata


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    bio = Column(String(256))
    password = Column(String(256), nullable=False)  # hashed password




    def __repr__(self):
        return f"Username: {self.name}, created_at: {self.created_at}"

