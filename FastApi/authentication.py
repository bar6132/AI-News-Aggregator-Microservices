import os
import jwt
from datetime import datetime, timedelta
from jwt import encode as jwt_encode, ExpiredSignatureError
from dotenv import load_dotenv

SECRET_KEY = os.getenv("SECRET_KEY", "8d32bfdb101ae60a669b6813e86ce5e5268197f0")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(user_id: int):
    try:
        data = {
            "sub": str(user_id),  # Assuming user_id is an integer, convert it to string for JWT
            "user_id": user_id,  # Add user_id directly to the JWT payload
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        encoded_jwt = jwt_encode(data, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except ExpiredSignatureError:
        raise ValueError("Token has expired")


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload)
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None