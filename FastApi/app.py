import os
import httpx
import requests
import jwt
import logging
from fastapi import FastAPI, HTTPException, Depends, Request, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from authentication import *
from dotenv import load_dotenv
from starlette.responses import RedirectResponse, JSONResponse
from models import UserCreate, UserLogin, validate_preferences
from datetime import datetime, timedelta
from typing import Dict, List


load_dotenv()
SERVICE_B_URL = os.getenv('SERVICE_B_URL', 'http://localhost:5000')
SECRET_KEY = "8d32bfdb101ae60a669b6813e86ce5e5268197f0"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
MANAGER_APP_ID = "flaskmanager"


app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Redirect from / to /docs where the swagger is
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# call_service_b check connection to the manager app
@app.get("/call_service_b")
def call_service_b():
    try:
        response = requests.get(f"{SERVICE_B_URL}/call_service_b")
        response.raise_for_status()
        logger.info(f"Service B says: {response.json()}")
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Request failed: {e}")
    return {"Service B says": response.json()}




@app.post("/signup")
def signup(user: UserCreate):
    try:
        # The UserCreate model now validates preferences during instantiation
        response = requests.post(f"{SERVICE_B_URL}/signup", json=user.dict())
        response.raise_for_status()  # Raise an exception for HTTP errors (status >= 400)

        # If the response is successful, return the JSON data
        return response.json()

    except requests.RequestException as e:
        # Handle any request exceptions (e.g., network issues, server errors)
        raise HTTPException(status_code=500, detail=f"Error during signup: {str(e)}")

    except HTTPException as e:
        # Handle HTTP errors from the SERVICE_B_URL endpoint
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# Endpoint for login and token generation
@app.post("/token", include_in_schema=False)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        response = requests.post(f"{SERVICE_B_URL}/login",
                                 json={"username": form_data.username, "password": form_data.password})
        response.raise_for_status()
        user = response.json()

        # Check if 'username' is present in the response
        if 'username' not in user:
            raise ValueError("Unexpected response format: 'username' not found in response")

        # Create access token
        access_token = create_access_token(user_id=user["user_id"])

        print({"message": "You are logged in!", "user": user["user_id"]})
        return {"access_token": access_token, "token_type": "bearer"}

    except requests.RequestException as e:
        raise HTTPException(status_code=401, detail=f"Error during authentication: {str(e)}")
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=str(ve))


async def get_current_user(token: str = Security(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("Decoded JWT payload:", payload)  # Print payload for inspection
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/login")
async def login(user: dict = Depends(get_current_user)):
    return {"message": "You are logged in!", "user": user["sub"]}


@app.get("/users/me/preferences")
async def read_user_preferences(
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    print("Requested user ID:", user_id)

    try:
        # Fetch user preferences from Flask manager using async HTTP client
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SERVICE_B_URL}/users/{user_id}/preferences")
            response.raise_for_status()

            return response.json()

    except HTTPException as e:
        raise e
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error from Flask manager: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.put("/users/me/preferences/update")
async def update_user_preferences(
    preferences_update: List[str],  # Expecting a list of strings
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    print("Updating preferences for user ID:", user_id)
    print("Received preferences update:", preferences_update)  # Log received data for debugging

    # Validate preferences before making the request
    try:
        preferences_update = validate_preferences(preferences_update)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        async with httpx.AsyncClient() as client:
            # Send preferences update to Flask manager
            update_response = await client.put(
                f"{SERVICE_B_URL}/users/{user_id}/preferences/update",
                json={"preferences": preferences_update}
            )
            update_response.raise_for_status()

            return {"message": "Preferences updated successfully"}

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error from Flask manager: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/call_service_b/news")
def call_service_b_news():
    try:
        response = requests.get(f"{SERVICE_B_URL}/call_service_b/news")
        response.raise_for_status()
        logger.info(f"Service B says: {response.json()}")
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Request failed: {e}")
    return {"Service B says": response.json()}


async def fetch_user_preferences(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVICE_B_URL}/users/{user_id}/preferences")
        response.raise_for_status()
        preferences = response.json().get("preferences", [])
    return preferences


@app.get("/users/me/news")
async def get_news(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    timeout = httpx.Timeout(5 * 60 * 60)
    # Fetch user preferences
    preferences = await fetch_user_preferences(user_id)

    # Send preferences to Flask manager
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{SERVICE_B_URL}/users/{user_id}/news",
                json={"preferences": preferences}
            )
            response.raise_for_status()
            news_data = response.json()
            logging.info(f"News data received: {news_data}")

        formatted_news = []
        for article in news_data.get("news", []):
            formatted_article = {
                "category": article.get("category"),
                "title": article.get("title"),
                "description": article.get("description"),
                'link': article.get("link"),
                "summary": article.get("summary")
            }
            formatted_news.append(formatted_article)

        return {"message": "News fetch request sent successfully", "news": formatted_news}
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error from News Aggregation Manager: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error from News Aggregation Manager: {e.response.text}")
    except Exception as e:
        logging.error(f"Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")



# @app.get("/users/me/news")
# async def get_news(current_user: dict = Depends(get_current_user)):
#     user_id = current_user.get("user_id")
#
#     # Fetch user preferences
#     preferences = await fetch_user_preferences(user_id)
#
#     # Send preferences to Flask manager
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{SERVICE_B_URL}/users/{user_id}/news",
#                 json={"preferences": preferences}
#             )
#             response.raise_for_status()
#             news_data = response.json()
#
#         return {"message": "News fetch request sent successfully", "news": news_data}
#
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error from News Aggregation Manager: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
#
#
# @app.put("/users/me/preferences/update")
# async def update_user_preferences(
#     preferences_update: list[str],  # Expecting a list of strings
#     current_user: dict = Depends(get_current_user),
# ):
#     user_id = current_user.get("user_id")
#     print("Updating preferences for user ID:", user_id)
#     print("Received preferences update:", preferences_update)  # Log received data for debugging
#
#     try:
#         async with httpx.AsyncClient() as client:
#             # Send preferences update to Flask manager
#             update_response = await client.put(
#                 f"{SERVICE_B_URL}/users/{user_id}/preferences/update",
#                 json={"preferences": preferences_update}
#             )
#             update_response.raise_for_status()
#
#             return {"message": "Preferences updated successfully"}
#
#     except httpx.HTTPStatusError as e:
#         raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error from Flask manager: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Endpoint for user signup
# @app.post("/signup")
# def signup(user: UserCreate):
#     try:
#         # Make a POST request to the SERVICE_B_URL endpoint with JSON data
#         response = requests.post(f"{SERVICE_B_URL}/signup", json=user.dict())
#         response.raise_for_status()  # Raise an exception for HTTP errors (status >= 400)
#
#         # If the response is successful, return the JSON data
#         return response.json()
#
#     except requests.RequestException as e:
#         # Handle any request exceptions (e.g., network issues, server errors)
#         raise HTTPException(status_code=500, detail=f"Error during signup: {str(e)}")
#
#     except HTTPException as e:
#         # Handle HTTP errors from the SERVICE_B_URL endpoint
#         raise HTTPException(status_code=e.status_code, detail=e.detail)
