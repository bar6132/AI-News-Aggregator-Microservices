
# Personalized News Update Aggregator

## Overview
This project is a microservice-based application designed to aggregate news and technology updates based on user preferences. The system fetches the latest news, uses AI to select the most interesting news based on user preferences, and optionally generates concise summaries using AI. The information is then sent to users via email and via Telegram to the project Manager.

## Features
- **User Management:** Users can Register/Login and update their preferences for news categories and technology updates.
- **News Aggregation:** The application fetches the latest news based on user preferences and sends the most interesting news to users.
- **AI Summarization :** Generates concise summaries of news articles using AI.
- **Notifications:** Sends news updates to users via email, Telegram.

## Microservices
1. **FastAPI Service:** Handles user requests.
2. **Flask Manager Service:** Manages data flow between microservices and forwards requests.
3. **News Aggregation Service:** Fetches and caches news articles based on user preferences.
4. **User Management Service:** Manages user data, login, signup, authentication, and preferences management.
5. **Telegram Service:** Send the news updates to manager via Telegram .
6. **Email Service:** Sends news updates to users via Email (SMTP).


## Technologies Used
- **FastAPI:** For creating RESTful APIs as well as Client Swagger For better UI.
- **Flask:** For microservices and inter-service communication.
- **Dapr:** For service invocation and message passing.
- **Docker:** For containerization of microservices.
- **RabbitMQ:** For message queuing.
- **Pickle:** For caching mechanism.
- **Gemini:** For AI-based summarization.


## Project Structure
```
/project-root
    ├── fastapi-service
    │   ├── app.py
    │   └── ...
    ├── flask-manager-service
    │		├── news-aggregation-service
    │   	├── app.py
    │   	└── ...
    │  	├── user-management-service
    │   	├── app.py
    │   	└── ...
    │		├── tel_bot
    │   	├── app.py
    │   	└── ...
    │  	├── email_bot
    │   	├── app.py
    │   	└── ...
    │   ├── manager_app.py
    │   └── ...
    ├── docker-compose.yml
    └── README.md
```

## Setup and Installation
1. **Clone the repository:**
    ```bash 
	git clone https://github.com/bar6132/Zionned-Final
        cd Zionned-Final
    ```
2. **Build and run the services using Docker Compose:**
    ```bash
    docker-compose up --build
    ```
3. **Access the services:**
    - FastAPI Service: `http://localhost:8000` Via Browser
    - Flask Manager Service: Accessible via FastAPI Service
    - News Aggregation Service: Accessible via Flask Manager
    - User Management Service: Accessible via Flask Manager

## Usage
1. **Setting User Signup:** Users need to signup via the FastAPI endpoint </signup>
       and will need to enter the following data {
  									"username": "string",
  									"password": "string",
 									 "email": "user@example.com",
  									"preferences": [] } . 

2. ** User Login:** Users will need to login using the Lock button<Authorize> or and Lock button
near the relevant  FastAPI endpoint.

3. **Update User Preferences:** Users can update their news category preferences via the FastAPI endpoints max 5 Preferences from the following:
Preferences = ["business", "crime", "domestic", "education", "entertainment",
                        "environment", "food", "health", "lifestyle", "other", "politics",
                        "science", "sports", "technology", "top", "tourism", "world"].

4. **Fetching News:** The system fetches and caches news articles based on user preferences. Cached news is returned if the same request is made within 24 hours.

5. **Notifications:** Users receive notifications about the latest news articles via their Email.


## Cache Mechanism
- **Loading Cache:** Cache is loaded from a file at the start of the application if it's empty.
- **Saving Cache:** Cache is saved to a file whenever updated to ensure persistence.
- **Fetching and Caching News:** News articles are fetched, processed, and stored in the cache with a timestamp.
- **Using Cached Data:** Cached data is used if valid (within 24 hours).