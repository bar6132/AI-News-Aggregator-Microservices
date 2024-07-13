import os
import httpx
import requests
import jwt
import logging
from fastapi import FastAPI, HTTPException, Depends, Request, Security, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from authentication import *
from dotenv import load_dotenv
from starlette.responses import RedirectResponse, JSONResponse
from models import UserCreate, UserLogin, validate_preferences
from datetime import datetime, timedelta
from typing import Dict, List
import subprocess

load_dotenv()
SERVICE_B_URL = os.getenv('SERVICE_B_URL', 'http://localhost:5000')
SECRET_KEY = os.getenv("SECRET_KEY", "8d32bfdb101ae60a669b6813e86ce5e5268197f0")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

MANAGER_APP_ID = "flaskmanager"

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def fetch_user_preferences(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVICE_B_URL}/users/{user_id}/preferences")
        response.raise_for_status()
        json_response = response.json()
        logging.info(f"Response from {SERVICE_B_URL}/users/{user_id}/preferences: {json_response}")

        # Extract and log preferences, username, and email
        preferences = json_response.get("preferences")
        username = json_response.get("username")
        email = json_response.get("email")
        print("Preferences:", preferences)
        print("Username:", username)
        print("Email:", email)

        # Check if any of the expected fields are missing
        if preferences is None or username is None or email is None:
            logging.error(f"Missing data in response: {json_response}")
            return None

    return preferences, username, email


async def get_current_user_dapr(token: str = Security(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("Decoded JWT payload:", payload)  # Print payload for inspection
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Redirect from / to /docs where the swagger is
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/call_service_b")
async def call_service_b():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://flaskmanager:3500/v1.0/invoke/flaskmanager/method/call_service_b")
            response.raise_for_status()
            logger.info(f"Service B says: {response.json()}")
            return {"Service B says": response.json()}
    except httpx.RequestError as e:
        logger.error(f"Request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Request failed: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {e}")
    
@app.get("/call_service_u")
async def call_service_u():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://flaskmanager:3500/v1.0/invoke/flaskmanager/method/call_service_u")
            response.raise_for_status()
            logger.info(f"Service U says: {response.json()}")
            return {"Service U says": response.json()}
    except httpx.RequestError as e:
        logger.error(f"Request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Request failed: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {e}")


@app.get("/call_service_n")
async def call_service_n():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://flaskmanager:3500/v1.0/invoke/flaskmanager/method/call_service_n")
            response.raise_for_status()
            logger.info(f"Service U says: {response.json()}")
            return {"Service U says": response.json()}
    except httpx.RequestError as e:
        logger.error(f"Request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Request failed: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {e}")


@app.post("/signup")
async def signup(user: UserCreate):
    try:
        async with httpx.AsyncClient() as client:
            # Use Dapr to invoke the service
            response = await client.post(
                f"http://flaskmanager:3500/v1.0/invoke/flaskmanager/method/signup",
                json=user.dict()
            )
            response.raise_for_status()  # Raise an exception for HTTP errors (status >= 400)

            # If the response is successful, return the JSON data
            return response.json()

    except httpx.RequestError as e:
        # Handle any request exceptions (e.g., network issues, server errors)
        raise HTTPException(status_code=500, detail=f"Error during signup: {str(e)}")

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors from the SERVICE_B_URL endpoint
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/token", include_in_schema=False)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://flaskmanager:3500/v1.0/invoke/flaskmanager/method/login",
                json={"username": form_data.username, "password": form_data.password}
            )
            response.raise_for_status()
            user = response.json()

        if 'username' not in user:
            raise ValueError("Unexpected response format: 'username' not found in response")

        # Create access token
        access_token = create_access_token(user_id=user["user_id"])

        return {"access_token": access_token, "token_type": "bearer"}

    except httpx.RequestError as e:
        raise HTTPException(status_code=401, detail=f"Error during authentication: {str(e)}")
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=str(ve))


async def get_current_user(token: str = Security(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/login")
async def login(user: dict = Depends(get_current_user)):
    return {"message": "You are logged in!", "user": user["sub"]}


@app.get("/users/me/preferences")
async def read_user_preferences(current_user: dict = Depends(get_current_user_dapr)):
    user_id = current_user.get("user_id")
    print("Requested user ID:", user_id)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://flaskmanager:3500/v1.0/invoke/flaskmanager/method/users/{user_id}/preferences",
                headers={"Accept": "application/json"}  # Ensure the correct headers are set
            )
            response.raise_for_status()
            json_response = response.json()

            # Debugging: Print the fetched preferences
            print("Fetched user preferences:", json_response)
            return json_response

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error from Flask manager: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.put("/users/me/preferences/update")
async def update_user_preferences(
        preferences_update: List[str],  # Expecting a list of strings,  # Expecting a list of strings
        current_user: dict = Depends(get_current_user), ):
    user_id = current_user.get("user_id")
    print("Updating preferences for user ID:", user_id)
    print("Received preferences update:", preferences_update)  # Log received data for debugging

    try:
        async with httpx.AsyncClient() as client:
            # Send preferences update to Flask manager via Dapr
            update_response = await client.put(
                f"http://flaskmanager:3500/v1.0/invoke/flaskmanager/method/users/{user_id}/preferences/update",
                json={"preferences": preferences_update}
            )
            update_response.raise_for_status()

            return {"message": "Preferences updated successfully"}

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error from Flask manager: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/users/me/news")
async def get_news(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    timeout = httpx.Timeout(5 * 60 * 60)

    # Fetch user preferences
    preferences, username, email = await fetch_user_preferences(user_id)

    background_tasks.add_task(send_news_request, user_id, preferences, username, email, timeout)

    return {"message": "News fetch request sent successfully and will be processed soon."}

async def send_news_request(user_id, preferences, username, email, timeout):
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"http://flaskmanager:3500/v1.0/invoke/flaskmanager/method/users/{user_id}/news",
                json={"preferences": preferences, "username": username, "email": email}
            )
            response.raise_for_status()
            logging.info(f"News fetch request processed successfully for user {user_id}")
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error from News Aggregation Manager: {e.response.text}")
    except Exception as e:
        logging.error(f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

