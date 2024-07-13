import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import json
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YOUR_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={YOUR_CHAT_ID}&text={message}"
    response = requests.post(url)
    return response.json()


@app.route("/receive_data", methods=["POST"])
def receive_data():
    data = request.json
    # Extract and format the message
    username = request.json.get("username")
    email = request.json.get("email")
    items = data.get('news', [])
    message_parts = [f"User: {username}\nEmail: {email}\n"]

    for item in items:
        category = ", ".join(item['category']) if isinstance(item['category'], list) else item['category']
        summary = item['summary']
        if isinstance(summary, str):
            try:
                summary_dict = json.loads(summary)  # Convert string representation of dictionary to actual dictionary
                summary = summary_dict.get('summary', summary)
            except json.JSONDecodeError:
                pass

        message_parts.append(
            f"Category: {category}\n"
            f"Title: {item['title']}\n"
            f"Description: {item['description']}\n"
            f"Link:{item['link']}'\n"
            f"Summary: {summary}"
        )

    message = "\n\n".join(message_parts)
    print(message)

    # Send the received data to your Telegram bot
    send_telegram_message(f"Received news data:\n\n{message}")

    # Respond with a success message
    return jsonify(
        {"status": "success", "message": "News data received and sent to Telegram successfully", "received_data": data})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003, debug=True)

