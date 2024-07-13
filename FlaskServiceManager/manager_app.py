from dotenv import load_dotenv
from flask import Flask, request, jsonify, abort
import requests
import os
import logging
import pika
import json
import httpx
from threading import Thread


app = Flask(__name__)
load_dotenv()

USER_MANAGEMENT_URL = os.getenv('USER_MANAGEMENT_URL', 'http://localhost:8001')
NEWS_AGGREGATION_URL = os.getenv('NEWS_AGGREGATION_URL', 'http://localhost:8002')
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_to_rabbitmq(queue, message):
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        ))
    connection.close()


@app.route("/call_service_b", methods=["GET"])
def call_service_b():
    print("Received a request at call_service_b", flush=True)
    return jsonify({"message": "Hello from Flask manager!"})



@app.route("/call_service_u", methods=["GET"])
def call_service_u():
    try:
        print("Received a request at /call_service_u", flush=True)
        with httpx.Client() as client:
            response = client.get("http://user_management:3503/v1.0/invoke/user_management/method/call_service_u")
            response.raise_for_status()
            json_response = response.json()
            return jsonify(json_response), 200
    except httpx.HTTPStatusError as e:
        return jsonify({"error": f"HTTP error from User Management Service: {e}"}), e.response.status_code
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/call_service_n", methods=["GET"])
async def call_service_n():
    try:
        print("Received a request at /call_service_n", flush=True)
        async with httpx.AsyncClient() as client:
            response = await client.get("http://news_aggregation:3502/v1.0/invoke/news_aggregation/method/call_service_n")
            response.raise_for_status()
            json_response = response.json()
            return jsonify(json_response), 200
    except httpx.HTTPStatusError as e:
        return jsonify({"error": f"HTTP error from News Aggregation Service: {e}"}), e.response.status_code
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/signup', methods=['POST'])
def forward_signup():
    print(f"Received a request at /signup", flush=True)
    data = request.get_json()
    print(f"Request data: {data}", flush=True)
    try:
        send_to_rabbitmq('signup_queue', data)
        return jsonify({"message": "Signup request sent successfully"})
    except Exception as e:
        return jsonify(error=f"Error during signup: {str(e)}"), 500


@app.route('/login', methods=['POST'])
async def forward_login():
    print(f"Received a request at /login", flush=True)
    data = request.get_json()
    print(f"Request data: {data}", flush=True)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://user_management:3503/v1.0/invoke/user_management/method/login", json=data)
            response.raise_for_status()
            return jsonify(response.json())

    except httpx.RequestError as e:
        app.logger.error(f"Error during login: {str(e)}")
        return jsonify(error=f"Error during login: {str(e)}"), 500


@app.route("/users/<int:user_id>/preferences", methods=["GET"])
async def get_user_preferences(user_id):
    try:
        print(f"Received a request at /users/{user_id}/preferences", flush=True)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://user_management:3503/v1.0/invoke/user_management/method/users/{user_id}/preferences"
                , headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            json_response = response.json()

            return jsonify(json_response), 200

    except httpx.HTTPStatusError as e:
        abort(e.response.status_code, description=f"HTTP error from User Management Service: {e}")
    except Exception as e:
        abort(500, description=f"Internal server error: {str(e)}")


@app.route("/users/<int:user_id>/preferences/update", methods=["PUT"])
async def update_user_preferences(user_id):
    print(f"Received a request at users/{user_id}/preferences/update", flush=True)

    try:
        # Extract preferences update from request body
        preferences_update = request.json.get("preferences")  # Assuming preferences are sent in the request body
        print(preferences_update)

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://user_management:3503/v1.0/invoke/user_management/method/users/{user_id}/preferences/update",
                json={"preferences": preferences_update}
            )
            response.raise_for_status()
            return jsonify(response.json()), response.status_code

    except httpx.RequestError as e:
        return jsonify(error=f"Error connecting to User Management Service: {str(e)}"), 500
    except httpx.HTTPStatusError as e:
        return jsonify(error=f"HTTP error: {str(e)}"), e.response.status_code
    except Exception as e:
        return jsonify(error=f"An error occurred: {str(e)}"), 500

@app.route("/users/<int:user_id>/news", methods=["POST"])
def fetch_news(user_id):
    try:
        preferences = request.json.get("preferences")
        username = request.json.get("username")
        email = request.json.get("email")

        if not preferences:
            abort(400, description="Preferences are required")

        # Forward the request to the News Aggregation Service via a background thread
        Thread(target=forward_news_request, args=(user_id, preferences, username, email)).start()

        return jsonify({"message": "News fetch request accepted and will be processed soon."})
    except Exception as e:
        logging.error(f"Request failed: {str(e)}")
        abort(500, description=f"Request failed: {str(e)}")

def forward_news_request(user_id, preferences, username, email):
    try:
        response = requests.post(
            f"http://news_aggregation:3502/v1.0/invoke/news_aggregation/method/users/{user_id}/news",
            json={"preferences": preferences, "username": username, "email": email}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Request to News Aggregation Service failed: {str(e)}")



if __name__ == "__main__":
    logging.info("Flask manager Application started ")
    app.run(host="0.0.0.0", port=80, debug=True)