import pika
import json
from database import get_db
from models import User
import bcrypt
from sqlalchemy.orm import Session
import logging
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
RABBITMQ_URL = "amqp://guest:guest@rabbitmq:5672/"


def process_signup(ch, method, properties, body):
    data = json.loads(body)
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    preferences = data.get("preferences", [])

    try:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        db: Session = next(get_db())

        # Check if email already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            logger.warning(f"Signup attempt with existing email {email}.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        db_user = User(
            username=username,
            hashed_password=hashed_password.decode('utf-8'),
            email=email,
            preferences=preferences
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        logger.info(f"User {username} signed up with email {email}.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Failed to process signup: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def consume_from_queue(queue_name, callback):
    max_retries = 5
    attempt = 0
    while attempt < max_retries:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=callback)
            logger.info(f"Started consuming from queue {queue_name}...")
            channel.start_consuming()
            break
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            attempt += 1
            sleep_time = 2 ** attempt
            logger.info(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break


def start_consumers():
    import threading
    threading.Thread(target=consume_from_queue, args=('signup_queue', process_signup)).start()
