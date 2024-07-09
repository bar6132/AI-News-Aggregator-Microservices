from dotenv import load_dotenv
from flask import Flask, request, jsonify, abort
import requests
from requests.exceptions import RequestException
import os
import logging
import pika
import json


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


@app.route('/call_service_b')
def endpoint_b():
    return jsonify(message="Hello from Service B")


@app.route("/call_service_b/news", methods=["GET"])
def endpoint_b_news():
    url = f"{NEWS_AGGREGATION_URL}/call"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        abort(500, description=f"Request failed: {str(e)}")


@app.route('/signup', methods=['POST'])
def forward_signup():
    try:
        data = request.get_json()
        send_to_rabbitmq('signup_queue', data)
        return jsonify({"message": "Signup request sent successfully"})
    except Exception as e:
        return jsonify(error=f"Error during signup: {str(e)}"), 500


@app.route('/login', methods=['POST'])
def forward_login():
    try:
        data = request.get_json()
        response = requests.post(f"{USER_MANAGEMENT_URL}/login", json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors (status >= 400)
        return jsonify(response.json())

    except RequestException as e:
        app.logger.error(f"Error during login: {str(e)}")
        return jsonify(error=f"Error during login: {str(e)}"), 500


@app.route("/users/<int:user_id>/preferences", methods=["GET"])
def get_user_preferences(user_id):
    try:
        # Forwarding the request to User Management Service
        url = f"{USER_MANAGEMENT_URL}/users/{user_id}/preferences"
        headers = {"Content-Type": "application/json"}
        response = requests.get(url, headers=headers)

        # Checking the response status code
        if response.status_code == 200:
            return jsonify(response.json()), 200
        elif response.status_code == 404:
            abort(404, description="User not found")
        elif response.status_code == 403:
            abort(403, description="Not authorized to access this user's preferences")
        else:
            abort(response.status_code, description="Failed to fetch user preferences")
    except requests.RequestException as e:
        abort(500, description=f"Error connecting to User Management Service: {str(e)}")


@app.route("/users/<int:user_id>/preferences/update", methods=["PUT"])
def update_user_preferences(user_id):
    try:
        # Extract preferences update from request body
        preferences_update = request.json.get("preferences")  # Assuming preferences are sent in the request body
        print(preferences_update)
        # Define the URL for the User Management Service
        url = f"{USER_MANAGEMENT_URL}/users/{user_id}/preferences/update"

        # Headers for the request
        headers = {"Content-Type": "application/json"}

        # Sending a PUT request to update user preferences
        response = requests.put(url, json={"preferences": preferences_update}, headers=headers)

        # Checking the response status code
        if response.status_code == 200:
            return jsonify(response.json()), 200
        elif response.status_code == 404:
            abort(404, description="User not found")
        elif response.status_code == 403:
            abort(403, description="Not authorized to update this user's preferences")
        else:
            abort(response.status_code, description="Failed to update user preferences")

    except requests.RequestException as e:
        abort(500, description=f"Error connecting to User Management Service: {str(e)}")

    except Exception as e:
        abort(500, description=f"An error occurred: {str(e)}")


@app.route("/users/<int:user_id>/news", methods=["POST"])
def fetch_news(user_id):
    try:
        # Extract preferences from the request body
        preferences = request.json.get("preferences")
        if not preferences:
            abort(400, description="Preferences are required")

        # Forward the request to the News Aggregation Service
        response = requests.post(f"{NEWS_AGGREGATION_URL}/users/{user_id}/news", json={"preferences": preferences})
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        logging.error(f"Request failed: {str(e)}")
        abort(500, description=f"Request failed: {str(e)}")


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=80, debug=True)
    except Exception as e:
        print(f"Exception occurred: {e}")




# @app.route("/users/<int:user_id>/news", methods=["POST"])
# def fetch_news(user_id):
#     try:
#         # Extract preferences from the request body
#         preferences = request.json.get("preferences")
#         if not preferences:
#             abort(400, description="Preferences are required")
#
#         # Send message to RabbitMQ
#         message = {
#             "user_id": user_id,
#             "preferences": preferences
#         }
#         send_to_rabbitmq('news_queue', message)
#
#         return jsonify({"message": "News fetch request sent successfully"})
#     except requests.RequestException as e:
#         logging.error(f"Request failed: {str(e)}")
#         abort(500, description=f"Request failed: {str(e)}")
#
# @app.route('/call_service_b')
# def endpoint_b():
#     return jsonify(message="Hello from Service B")
#
#
# @app.route("/call_service_b/news", methods=["GET"])
# def endpoint_b_news():
#     url = f"{NEWS_AGGREGATION_URL}/call"
#     headers = {"Content-Type": "application/json"}
#     try:
#         response = requests.get(url, headers=headers)
#         response.raise_for_status()
#         return jsonify(response.json())
#     except requests.RequestException as e:
#         abort(500, description=f"Request failed: {str(e)}")
#
#
# @app.route('/signup', methods=['POST'])
# def forward_signup():
#     try:
#         data = request.get_json()
#         response = requests.post(f"{USER_MANAGEMENT_URL}/signup", json=data)
#         response.raise_for_status()  # Raise an exception for HTTP errors (status >= 400)
#         return jsonify(response.json())
#
#     except requests.RequestException as e:
#         return jsonify(error=f"Error during signup: {str(e)}"), 500
#
#
# @app.route('/login', methods=['POST'])
# def forward_login():
#     try:
#         data = request.get_json()
#         response = requests.post(f"{USER_MANAGEMENT_URL}/login", json=data)
#         response.raise_for_status()  # Raise an exception for HTTP errors (status >= 400)
#         return jsonify(response.json())
#
#     except RequestException as e:
#         app.logger.error(f"Error during login: {str(e)}")
#         return jsonify(error=f"Error during login: {str(e)}"), 500
#
#
# @app.route("/users/<int:user_id>/preferences", methods=["GET"])
# def get_user_preferences(user_id):
#     try:
#         # Forwarding the request to User Management Service
#         url = f"{USER_MANAGEMENT_URL}/users/{user_id}/preferences"
#         headers = {"Content-Type": "application/json"}
#         response = requests.get(url, headers=headers)
#
#         # Checking the response status code
#         if response.status_code == 200:
#             return jsonify(response.json()), 200
#         elif response.status_code == 404:
#             abort(404, description="User not found")
#         elif response.status_code == 403:
#             abort(403, description="Not authorized to access this user's preferences")
#         else:
#             abort(response.status_code, description="Failed to fetch user preferences")
#     except requests.RequestException as e:
#         abort(500, description=f"Error connecting to User Management Service: {str(e)}")
#
#
# @app.route("/users/<int:user_id>/preferences/update", methods=["PUT"])
# def update_user_preferences(user_id):
#     try:
#         # Extract preferences update from request body
#         preferences_update = request.json.get("preferences")  # Assuming preferences are sent in the request body
#         print(preferences_update)
#         # Define the URL for the User Management Service
#         url = f"{USER_MANAGEMENT_URL}/users/{user_id}/preferences/update"
#
#         # Headers for the request
#         headers = {"Content-Type": "application/json"}
#
#         # Sending a PUT request to update user preferences
#         response = requests.put(url, json={"preferences": preferences_update}, headers=headers)
#
#         # Checking the response status code
#         if response.status_code == 200:
#             return jsonify(response.json()), 200
#         elif response.status_code == 404:
#             abort(404, description="User not found")
#         elif response.status_code == 403:
#             abort(403, description="Not authorized to update this user's preferences")
#         else:
#             abort(response.status_code, description="Failed to update user preferences")
#
#     except requests.RequestException as e:
#         abort(500, description=f"Error connecting to User Management Service: {str(e)}")
#
#     except Exception as e:
#         abort(500, description=f"An error occurred: {str(e)}")
#
# ######################################################################
# ######################################################################
# ######################################################################
# ######################################################################
#
#
# @app.route("/users/<int:user_id>/news", methods=["POST"])
# def fetch_news(user_id):
#     try:
#         # Extract preferences from the request body
#         preferences = request.json.get("preferences")
#         if not preferences:
#             abort(400, description="Preferences are required")
#
#         # Forward the request to the News Aggregation Service
#         response = requests.post(f"{NEWS_AGGREGATION_URL}/users/{user_id}/news", json={"preferences": preferences})
#         response.raise_for_status()
#         return jsonify(response.json())
#     except requests.RequestException as e:
#         logging.error(f"Request failed: {str(e)}")
#         abort(500, description=f"Request failed: {str(e)}")

