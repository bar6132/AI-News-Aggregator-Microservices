from flask import Flask, request, jsonify, abort
import os
import logging
import time
import asyncio
import pickle
from aiohttp import ClientSession
import google.generativeai as genai
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

logging.basicConfig(level=logging.INFO)


BASE_URL = os.getenv('BASE_URL')
API_KEY = os.getenv('API_KEY')
VALID_CATEGORIES = ["business", "crime", "domestic", "education", "entertainment",
                    "environment", "food", "health", "lifestyle", "other", "politics",
                    "science", "sports", "technology", "top", "tourism", "world"]
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

genai.configure(api_key=GOOGLE_API_KEY)
# Cache file path
CACHE_FILE_PATH = "news_cache.pkl"
# Cache dictionary
news_cache = {}
# Cache expiry time (24 hours)
CACHE_EXPIRY = 24 * 60 * 60  # 24 hours in seconds


@app.route("/call", methods=["GET"])
def call_service_b():
    return jsonify({"message": "Hello from News Aggregation Manager!"})


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


@app.route("/users/<int:user_id>/news", methods=["POST"])
async def fetch_latest_news(user_id):
    try:
        preferences = request.json.get("preferences")
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
                    # Filter out only the required fields
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

        return jsonify({"message": "News fetch request sent successfully", "news": news_articles})
    except Exception as e:
        logging.error(f"Internal server error: {str(e)}")
        abort(500, description=f"Internal server error: {str(e)}")

# async def generate_summary(article_link):
#     try:
#         prompt = f"""
#         Summarize this news article from the given link: {article_link}
#
#         Instructions:
#         - Make the summary interesting and engaging.
#         - Ensure the summary is concise and informative.
#         - Limit the summary to 3 lines, 4 lines maximum.
#         """
#
#         generation_config = {
#             "temperature": 1,
#             "top_p": 0.95,
#             "top_k": 64,
#             "max_output_tokens": 8192,
#             "response_mime_type": "application/json",
#         }
#
#         model = genai.GenerativeModel(
#             model_name="gemini-1.5-flash",
#             generation_config=generation_config,
#         )
#
#         response = model.generate_content(prompt)
#         summary = response.candidates[0].content.parts[0].text.strip()
#         logging.info(f"Generated summary: {summary}")
#         return {"summary": summary}
#     except Exception as e:
#         logging.error(f"Error generating summary: {str(e)}")
#         return {"summary": "Error generating summary"}
#
#
# async def fetch_and_summarize_news_for_category(session, category):
#     try:
#         url = f"{BASE_URL}?apikey={API_KEY}&language=en&category={category}"
#         async with session.get(url) as response:
#             logging.info(f"Fetching news for category: {category}, Status: {response.status}")
#             if response.status == 200:
#                 data = await response.json()
#                 logging.info(f"Data received for category {category}: {data}")
#                 if data['status'] == 'success' and 'results' in data and data['results']:
#                     first_article = data['results'][0]  # Take the first article only
#                     if 'link' in first_article and first_article['link']:
#                         summary = await generate_summary(first_article['link'])
#                         first_article.update(summary)
#                         logging.info(f"Processed article: {first_article}")
#                         return first_article
#             logging.error(f"Failed to fetch or find valid articles for category: {category}")
#             return None
#     except Exception as e:
#         logging.error(f"Error fetching news for category {category}: {str(e)}")
#         return None
#
# @app.route("/users/<int:user_id>/news", methods=["POST"])
# async def fetch_latest_news(user_id):
#     try:
#         preferences = request.json.get("preferences")
#         if not preferences:
#             logging.error("Preferences are required")
#             abort(400, description="Preferences are required")
#
#         valid_preferences = [cat for cat in preferences if cat in VALID_CATEGORIES][:5]
#         if not valid_preferences:
#             logging.error("No valid categories found")
#             abort(400, description="No valid categories found")
#
#         news_articles = []
#
#         async with aiohttp.ClientSession() as session:
#             tasks = [fetch_and_summarize_news_for_category(session, category) for category in valid_preferences]
#             results = await asyncio.gather(*tasks)
#
#             for article in results:
#                 if article:
#                     # Filter out only the required fields
#                     filtered_article = {
#                         "category": article.get("category"),
#                         "title": article.get("title"),
#                         "description": article.get("description"),
#                         'link': article.get("link"),
#                         "summary": article.get("summary"),
#                     }
#                     news_articles.append(filtered_article)
#
#         if not news_articles:
#             logging.error("No valid articles found")
#             abort(500, description="No valid articles found")
#
#         return jsonify({"message": "News fetch request sent successfully", "news": news_articles})
#     except Exception as e:
#         logging.error(f"Internal server error: {str(e)}")
#         abort(500, description=f"Internal server error: {str(e)}")


# async def fetch_news_for_category(session, category):
#     url = f"{BASE_URL}?apikey={API_KEY}&language=en&category={category}"
#     async with session.get(url) as response:
#         if response.status == 200:
#             data = await response.json()
#             if data['status'] == 'success' and 'results' in data and data['results']:
#                 article = data['results'][0]
#                 return {
#                     'headline': article.get('title'),
#                     'link': article.get('link'),
#                     'description': article.get('description', None)
#                 }
#         return None
#
#
# @app.route("/users/<int:user_id>/news", methods=["POST"])
# async def fetch_latest_news(user_id):
#     try:
#         # Extract preferences from the request body
#         preferences = request.json.get("preferences")
#         if not preferences:
#             abort(400, description="Preferences are required")
#
#         # Filter out invalid categories
#         valid_preferences = [cat for cat in preferences if cat in VALID_CATEGORIES]
#         if not valid_preferences:
#             abort(400, description="No valid categories found")
#
#         news_articles = {}
#
#         async with aiohttp.ClientSession() as session:
#             tasks = [fetch_news_for_category(session, category) for category in valid_preferences]
#             results = await asyncio.gather(*tasks)
#
#             for category, article in zip(valid_preferences, results):
#                 news_articles[category] = article
#
#         return jsonify(news_articles)
#     except Exception as e:
#         logging.error(f"Request failed: {str(e)}")
#         abort(500, description=f"Request failed: {str(e)}")


# async def fetch_news_for_category(session, category):
#     url = f"{BASE_URL}?apikey={API_KEY}&language=en&category={category}"
#     async with session.get(url) as response:
#         logging.info(f"Fetching news for category: {category}, Status: {response.status}")
#         if response.status == 200:
#             data = await response.json()
#             # logging.info(f"Data received for category {category}: {data}")
#             if data['status'] == 'success' and 'results' in data and data['results']:
#                 return data['results'][0]  # Get the first article for the category
#         else:
#             logging.error(f"Failed to fetch news for category: {category}, Status: {response.status}")
#         return None
#
# def generate_summary(article_link):
#     try:
#         prompt = f"""
#         Summarize this news article from the given link: {article_link}
#
#         Instructions:
#         - Make the summary interesting and engaging.
#         - Ensure the summary is concise and informative.
#         - Limit the summary to 3 lines, 4 lines maximum.
#         """
#
#         model = genai.GenerativeModel('gemini-1.5-flash')
#         response = model.generate_content(prompt)
#
#         summary = response.candidates[0].content.parts[0].text.strip()
#         logging.info(f"Generated summary: {summary}")
#         return {"summary": summary}
#     except Exception as e:
#         logging.error(f"Error generating summary: {str(e)}")
#         return {"summary": "Error generating summary"}
#
#
# @app.route("/users/<int:user_id>/news", methods=["POST"])
# async def fetch_latest_news(user_id):
#     try:
#         # Extract preferences from the request body
#         preferences = request.json.get("preferences")
#         if not preferences:
#             logging.error("Preferences are required")
#             abort(400, description="Preferences are required")
#
#         # Filter out invalid categories and limit to 5 preferences
#         valid_preferences = [cat for cat in preferences if cat in VALID_CATEGORIES][:5]
#         if not valid_preferences:
#             logging.error("No valid categories found")
#             abort(400, description="No valid categories found")
#
#         news_articles = []
#
#         async with aiohttp.ClientSession() as session:
#             tasks = [fetch_news_for_category(session, category) for category in valid_preferences]
#             results = await asyncio.gather(*tasks)
#
#             for category, article in zip(valid_preferences, results):
#                 if article:
#                     news_articles.append({
#                         'headline': article.get('title'),
#                         'link': article.get('link'),
#                         'description': article.get('description', None),
#                         'category': category
#                     })
#
#         if not news_articles:
#             logging.error("No valid articles found")
#             abort(500, description="No valid articles found")
#
#         # Generate summaries for selected articles
#         for article in news_articles:
#             article.update(generate_summary(article['link']))
#
#         return jsonify({"message": "News fetch request sent successfully", "news": news_articles})
#     except Exception as e:
#         logging.error(f"Internal server error: {str(e)}")
#         abort(500, description=f"Internal server error: {str(e)}")


if __name__ == '__main__':
    try:
        app.run(host="0.0.0.0", port=8002, debug=True)
    except Exception as e:
        print(f"Exception occurred: {e}")

