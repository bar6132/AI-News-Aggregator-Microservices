import os
from flask import Flask, jsonify
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import psycopg2
from psycopg2 import sql
import logging
from routes import bp as auth_bp
from database import Base, engine  # Import engine from database.py
from models import User  # Import the User model to ensure it's registered with SQLAlchemy
from consumers import process_signup, start_consumers
from sqlalchemy.orm import sessionmaker


app = Flask(__name__)
app.register_blueprint(auth_bp)

# Configuration
DB_USER = 'postgres'
DB_PASSWORD = 6132
DB_HOST = 'postgres'  # Use 'postgres' service name
DB_PORT = 5432
DB_NAME = 'Zionnet'
RABBITMQ_URL = "amqp://guest:guest@rabbitmq:5672/"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_database():
    try:
        conn = psycopg2.connect(
            dbname='postgres',
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(sql.SQL("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s"), [DB_NAME])
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            logger.info(f"Database {DB_NAME} created successfully.")
        else:
            logger.info(f"Database {DB_NAME} already exists.")

        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"An error occurred: {e}")


def create_tables():
    try:
        logger.info("Creating tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully (or already exist).")
    except Exception as e:
        logger.error(f"An error occurred while creating tables: {e}")


if __name__ == "__main__":
    start_consumers()  # Start RabbitMQ consumers
    create_database()  # Ensure database exists
    create_tables()  # Ensure tables are created
    logging.info("Application started and consumers are running.")
    app.run(host="0.0.0.0", port=8001, debug=True)
