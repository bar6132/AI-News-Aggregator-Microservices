from flask import Flask, request, jsonify, abort
import os
import logging
import time
import asyncio
import pickle
from aiohttp import ClientSession
import google.generativeai as genai
from dotenv import load_dotenv
import requests
app = Flask(__name__)
load_dotenv()

logging.basicConfig(level=logging.INFO)


BASE_URL = os.getenv('BASE_URL')
API_KEY = os.getenv('API_KEY')
VALID_CATEGORIES = ["business", "crime", "domestic", "education", "entertainment",
                    "environment", "food", "health", "lifestyle", "other", "politics",
                    "science", "sports", "technology", "top", "tourism", "world"]
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
TELEGRAM_BOT_URL = "http://telegram_bot:8003/receive_data"
EMAIL_SERVICE_URL = "http://email_service:8004/send_email"

genai.configure(api_key=GOOGLE_API_KEY)
# Cache file path
CACHE_FILE_PATH = "news_cache.pkl"
# Cache dictionary
news_cache = {}
# Cache expiry time (24 hours)
CACHE_EXPIRY = 24 * 60 * 60  # 24 hours in seconds


@app.route("/call_service_n", methods=["GET"])
def call_u():
    print("Received a request at call_n", flush=True)
    return jsonify({"message": "Hello from News Aggregation Manager!!"}), 200


def load_cache():
    """Load cache from a file."""
    global news_cache
    if os.path.exists(CACHE_FILE_PATH):
        with open(CACHE_FILE_PATH, "rb") as cache_file:
            news_cache = pickle.load(cache_file)
            logging.info("Cache loaded from file")


def save_cache():
    """Save cache to a file."""
    with open(CACHE_FILE_PATH, "wb") as cache_file:
        pickle.dump(news_cache, cache_file)
        logging.info("Cache saved to file")


@app.before_request
def initialize():
    """Load cache before the first request."""
    if not news_cache:  # Only load cache if it is empty
        load_cache()


async def generate_summary(article_link):
    try:
        prompt = f"""
        Summarize this news article from the given link: {article_link}

        Instructions:
        - Make the summary interesting and engaging.
        - Ensure the summary is concise and informative.
        - Limit the summary to 3 lines, 4 lines maximum.
        """

        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
        )

        response = model.generate_content(prompt)
        summary = response.candidates[0].content.parts[0].text.strip()
        logging.info(f"Generated summary: {summary}")
        return {"summary": summary}
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}")
        return {"summary": "Error generating summary"}


async def fetch_and_cache_news(session, category):
    """Fetch news for a category and update the cache."""
    url = f"{BASE_URL}?apikey={API_KEY}&language=en&category={category}"
    async with session.get(url) as response:
        logging.info(f"Fetching news for category: {category}, Status: {response.status}")
        if response.status == 200:
            data = await response.json()
            logging.info(f"Data received for category {category}: {data}")
            if data['status'] == 'success' and 'results' in data and data['results']:
                first_article = data['results'][0]  # Take the first article only
                if 'link' in first_article and first_article['link']:
                    summary = await generate_summary(first_article['link'])
                    first_article.update(summary)
                    first_article['category'] = list(set(first_article.get('category', [])))
                    news_cache[category] = {
                        "data": first_article,
                        "timestamp": time.time()
                    }
                    save_cache()  # Save cache to file after updating
                    logging.info(f"Cache updated for category {category}")
                    return first_article
        logging.error(f"Failed to fetch or find valid articles for category: {category}")
        return None


async def get_cached_or_fresh_news(session, category):
    """Get news from cache if fresh, otherwise fetch and update the cache."""
    current_time = time.time()
    if category in news_cache:
        cache_entry = news_cache[category]
        if current_time - cache_entry["timestamp"] < CACHE_EXPIRY:
            logging.info(f"Returning cached data for category {category}")
            return cache_entry["data"]

    # Cache is empty or stale, fetch fresh data
    logging.info(f"Cache expired or not found for category {category}, fetching fresh data")
    return await fetch_and_cache_news(session, category)


async def send_data_to_telegram_bot(news_data, username, email):
    try:
        async with ClientSession() as session:
            async with session.post(TELEGRAM_BOT_URL, json={"news": news_data,
                                                            "username": username,
                                                            "email": email
                                                            }) as response:
                response.raise_for_status()
                logging.info("Data sent to Telegram bot successfully")
    except Exception as e:
        logging.error(f"Failed to send data to Telegram bot: {str(e)}")


async def send_data_to_email_service(news_data, username, email):
    try:
        async with ClientSession() as session:
            async with session.post(EMAIL_SERVICE_URL, json={"news": news_data, "username": username, "email": email}) as response:
                response.raise_for_status()
                logging.info("Data sent to Email service successfully")
    except Exception as e:
        logging.error(f"Failed to send data to Email service: {str(e)}")


@app.route("/users/<int:user_id>/news", methods=["POST"])
async def fetch_latest_news(user_id):
    try:
        preferences = request.json.get("preferences")
        username = request.json.get("username")
        email = request.json.get("email")

        if not preferences:
            logging.error("Preferences are required")
            abort(400, description="Preferences are required")

        valid_preferences = [cat for cat in preferences if cat in VALID_CATEGORIES][:5]
        if not valid_preferences:
            logging.error("No valid categories found")
            abort(400, description="No valid categories found")

        news_articles = []

        async with ClientSession() as session:
            tasks = [get_cached_or_fresh_news(session, category) for category in valid_preferences]
            results = await asyncio.gather(*tasks)

            for article in results:
                if article:
                    filtered_article = {
                        "category": article.get("category"),
                        "title": article.get("title"),
                        "description": article.get("description"),
                        'link': article.get("link"),
                        "summary": article.get("summary"),
                    }
                    news_articles.append(filtered_article)

        if not news_articles:
            logging.error("No valid articles found")
            abort(500, description="No valid articles found")

        try:
            await send_data_to_telegram_bot(news_articles, username, email)
        except Exception as e:
            logging.error(f"Error sending data to Telegram bot: {str(e)}")

        try:
            await send_data_to_email_service(news_articles, username, email)
        except Exception as e:
            logging.error(f"Error sending data to Email service: {str(e)}")

        return jsonify({"message": "News fetch request processed successfully."})
    except Exception as e:
        logging.error(f"Internal server error: {str(e)}")
        abort(500, description=f"Internal server error: {str(e)}")
        

        
if __name__ == '__main__':
    try:
        app.run(host="0.0.0.0", port=8002, debug=True)
    except Exception as e:
        print(f"Exception occurred: {e}")




