# models/progress.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Float
from sqlalchemy.sql import func
from database import Base


class Progress(Base):
    __tablename__ = "progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String)
    accuracy = Column(Float, default=0.0)
    last_updated = Column(
        DateTime, server_default=func.now(), onupdate=func.now())
# abc
