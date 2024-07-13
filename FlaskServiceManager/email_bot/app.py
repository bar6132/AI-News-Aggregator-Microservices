from flask import Flask, request, jsonify
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv('SMTP_PORT')


def send_email(news_data, username, email):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Zion-net {EMAIL_ADDRESS}"
        msg['To'] = email
        msg['Subject'] = "Latest News"

        body = f"Hello {username},\n\nHere are the latest news articles based on your preferences:\n\n"
        for article in news_data:
            category = ", ".join(article['category']) if isinstance(article['category'], list) else article['category']
            summary = article['summary']
            if isinstance(summary, str):
                try:
                    summary_dict = json.loads(summary)
                    summary = summary_dict.get('summary', summary)
                except json.JSONDecodeError:
                    pass

            body += (
                f"Category: {category}\n"
                f"Title: {article['title']}\n"
                f"Description: {article['description']}\n"
                f"Link: {article['link']}\n"
                f"Summary: {summary}\n\n"
            )

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")


@app.route("/send_email", methods=["POST"])
def send_email_route():
    data = request.json
    news_data = data.get("news")
    username = request.json.get("username")
    email = request.json.get("email")
    print(email, news_data, username)
    send_email(news_data, username, email)

    return jsonify({"status": "success", "message": "Email sent successfully"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8004, debug=True)
