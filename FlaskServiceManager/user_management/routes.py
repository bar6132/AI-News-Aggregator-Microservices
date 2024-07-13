from flask import Blueprint, request, jsonify, abort
from sqlalchemy.orm import Session
from database import get_db
from models import User
import bcrypt
import logging
from sqlalchemy.exc import SQLAlchemyError
import pika
import json


bp = Blueprint('auth', __name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_URL = "amqp://guest:guest@rabbitmq:5672/"


# Function to send messages to RabbitMQ
def send_to_rabbitmq(queue_name, message):
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(message), properties=pika.BasicProperties(delivery_mode=2))
    connection.close()
    logger.info(f"Message sent to queue {queue_name}: {message}")


@bp.route("/signup", methods=["POST"])
def signup():
    print("Received a request at signup", flush=True)
    data = request.get_json()
    print(f"Received signup data: {data}")
    # Process the signup data here
    return jsonify({"message": "Signup request processed successfully"})


@bp.route("/login", methods=["POST"])
def login():
    print("Received a request at login", flush=True)
    data = request.get_json()
    print(f"Received login data: {data}")
    username = data.get("username")
    password = data.get("password")

    # Query the database for the user
    db: Session = next(get_db())
    db_user = db.query(User).filter(User.username == username).first()

    # Check if the user exists and verify the password
    if not db_user or not bcrypt.checkpw(password.encode('utf-8'), db_user.hashed_password.encode('utf-8')):
        logger.warning(f"Failed login attempt for username {username}.")
        return jsonify({"error": "Invalid username or password"}), 400

    # Log successful login
    logger.info(f"User {username} logged in successfully.")

    # Return success message and username
    print(db_user.id)
    return jsonify({"username": db_user.username, "user_id": db_user.id, "message": "Login successful"})


@bp.route("/call_service_u", methods=["GET"])
def call_u():
    print("Received a request at call_service_u", flush=True)
    return jsonify({"message": "Hello from User Management Service!"}), 200


@bp.route("/users/<int:user_id>/preferences", methods=["GET"])
def get_user_preferences(user_id):
    print(f"Received a request at /users/{user_id}/preferences", flush=True)
    try:
        db: Session = next(get_db())
        user = db.query(User).filter_by(id=user_id).first()

        if user is None:
            abort(404, description=f"User with id {user_id} not found")

        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "preferences": user.preferences
        }
        print(f"Received user data: {user_data}")
        return jsonify(user_data), 200

    except Exception as e:
        return jsonify({
            "error": f"An error occurred: {str(e)}"
        }), 500


@bp.route("/users/<int:user_id>/preferences/update", methods=["PUT"])
def update_user_preferences(user_id):
    print(f"Received a request at /users/{user_id}/preferences/update", flush=True)
    try:
        # Fetch preferences update from request body
        preferences_update = request.json.get("preferences")  # Assuming preferences are sent in the request body
        print("Received preferences update:", preferences_update)

        # Retrieve user from database
        db: Session = next(get_db())
        user = db.query(User).filter_by(id=user_id).first()
        print("Retrieved user:", user)

        # Check if user exists
        if user is None:
            abort(404, description=f"User with id {user_id} not found")

        # Update user preferences if preferences_update is not None
        if preferences_update is not None:
            user.preferences = preferences_update  # Assuming preferences is a list or JSON-compatible structure

        # Commit changes to database
        db.commit()

        # Return updated preferences as JSON response
        return jsonify({
            "message": "Preferences updated successfully",
            "user_id": user.id,
            "preferences": user.preferences
        }), 200

    except SQLAlchemyError as e:
        db.rollback()
        abort(500, description=f"Database error: {str(e)}")

    except Exception as e:
        abort(500, description=f"An error occurred: {str(e)}")
