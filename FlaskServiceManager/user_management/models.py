from sqlalchemy import Column, Integer, String, ARRAY
from database import Base


class User(Base):
    __tablename__ = "users" # This specifies the table name
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String, unique=True, index=True)
    preferences = Column(ARRAY(String), default=[], nullable=True)

