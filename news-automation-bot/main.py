import feedparser
import requests
import sqlite3
import time
import re
import os
from html import unescape


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@holovni_novyny_ua"

SOURCES = {
    "Ukrainska Pravda": "https://www.pravda.com.ua/rss/",
    "RBC-Ukraine": "https://www.rbc.ua/static/rss/all.ukr.rss.xml",
    "NV": "https://nv.ua/ukr/rss/all.xml"
}

CHECK_INTERVAL = 300
POST_DELAY = 5
MAX_NEWS_PER_SOURCE = 10


# ============================================================
# KEYWORDS FOR NEWS CLASSIFICATION
# ============================================================

STRONG_KEYWORDS = [
    "ракета",
    "ракет",
    "балістик",
    "обстріл",
    "обстріляли",
    "обстрілюють",
    "атака",
    "атакували",
    "атакував",
    "удар по",
    "бойове застосування",
    "зсу",
    "загинув",
    "загинули",
    "загибл",
    "поранен",
    "поранені",
    "окупація",
    "окупували",
    "шахед",
    "бпла",
    "безпілотник",
    "бойові дії"
]

MEDIUM_KEYWORDS = [
    "дрон",
    "дрони",
    "ппо",
    "фронт",
    "наступ",
    "відступ",
    "російські війська",
    "росіяни",
    "рф",
    "росія",
    "санкції",
    "нато",
    "мобілізація",
    "ядерн",
    "авіаудар",
    "артилерія",
    "танк",
    "снаряд",
    "боєприпас"
]

WEAK_KEYWORDS = [
    "президент",
    "зеленський",
    "уряд",
    "кабмін",
    "верховна рада",
    "єс",
    "сша",
    "закон"
]

EXCLUDED_PHRASES = [
    "атмосферний фронт",
    "холодний фронт",
    "теплий фронт",
    "фронт опадів"
]


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# NEWS CLASSIFICATION
# ============================================================

def classify_news(title, description):
    text = clean_text(f"{title} {description}").lower()

    score = 0
    matched_keywords = []

    # Strong keywords = 3 points
    for keyword in STRONG_KEYWORDS:
        if keyword.lower() in text:
            score += 3
            matched_keywords.append(f"{keyword} (+3)")

    # Medium keywords = 2 points
    for keyword in MEDIUM_KEYWORDS:

        keyword_lower = keyword.lower()

        # Ignore weather-related uses of "front"
        if keyword_lower == "фронт":
            if any(excluded in text for excluded in EXCLUDED_PHRASES):
                continue

        if keyword_lower in text:
            score += 2
            matched_keywords.append(f"{keyword} (+2)")

    # Weak keywords = 1 point
    for keyword in WEAK_KEYWORDS:
        if keyword.lower() in text:
            score += 1
            matched_keywords.append(f"{keyword} (+1)")

    # 3 or more points = important news
    if score >= 3:
        return "🔴 IMPORTANT", matched_keywords

    return "🟡 REGULAR", matched_keywords


# ============================================================
# TELEGRAM HTML
# ============================================================

def escape_html(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    return text


def make_post(title, description):
    title = clean_text(title)
    description = clean_text(description)

    title = escape_html(title)
    description = escape_html(description)

    if description:
        return f"<b>📰 {title}</b>\n\n{description}"

    return f"<b>📰 {title}</b>"


# ============================================================
# DATABASE
# ============================================================

def create_database():
    connection = sqlite3.connect("news.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS published_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE,
            title TEXT
        )
    """)

    connection.commit()
    connection.close()


def news_exists(link):
    connection = sqlite3.connect("news.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM published_news WHERE link = ?",
        (link,)
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


def save_news(link, title):
    connection = sqlite3.connect("news.db")
    cursor = connection.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO published_news (link, title) VALUES (?, ?)",
        (link, title)
    )

    connection.commit()
    connection.close()


# ============================================================
# IMAGE EXTRACTION
# ============================================================

def get_image(news):

    if news.get("media_content"):
        for media in news.media_content:

            image_url = media.get("url")

            if image_url:
                return image_url

    if news.get("media_thumbnail"):
        for media in news.media_thumbnail:

            image_url = media.get("url")

            if image_url:
                return image_url

    if news.get("enclosures"):
        for enclosure in news.enclosures:

            image_url = enclosure.get("href", "")

            if image_url:
                return image_url

    description = news.get(
        "summary",
        news.get("description", "")
    )

    image_match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        description,
        re.IGNORECASE
    )

    if image_match:
        return image_match.group(1)

    return None


# ============================================================
# TELEGRAM DELIVERY
# ============================================================

def send_to_telegram(message, image_url=None):

    try:

        if image_url:

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

            data = {
                "chat_id": CHANNEL_ID,
                "photo": image_url,
                "caption": message,
                "parse_mode": "HTML"
            }

        else:

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

            data = {
                "chat_id": CHANNEL_ID,
                "text": message,
                "parse_mode": "HTML"
            }

        response = requests.post(
            url,
            data=data,
            timeout=30
        )

        if response.status_code == 200:

            print("✅ Published successfully")

            return True

        elif response.status_code == 429:

            print("⚠️ Telegram rate limit reached")

            try:
                retry_after = response.json()["parameters"]["retry_after"]

            except Exception:
                retry_after = 60

            print(f"⏳ Waiting {retry_after} seconds...")

            time.sleep(retry_after)

            return False

        else:

            print("❌ Telegram API error:")
            print(response.text)

            return False

    except Exception as error:

        print("❌ Connection error:")
        print(error)

        return False


# ============================================================
# INITIALIZE EXISTING NEWS
# ============================================================

def initialize_existing_news():

    print("\n📚 First run: storing existing news...")

    total = 0

    for source_name, rss_url in SOURCES.items():

        print(f"\n📡 {source_name}")

        try:

            feed = feedparser.parse(rss_url)

            if not feed.entries:

                print("❌ No news found")

                continue

            for news in feed.entries[:MAX_NEWS_PER_SOURCE]:

                link = news.get("link", "")
                title = news.get("title", "Untitled")

                if not link:
                    continue

                if not news_exists(link):

                    save_news(link, title)

                    total += 1

                    print("📌 Stored:", title)

        except Exception as error:

            print("❌ Source error:")
            print(error)

    print(f"\n✅ Stored existing news: {total}")
    print("ℹ️ Existing news will not be published.")


# ============================================================
# NEWS CHECK
# ============================================================

def check_news():

    print("\n🔎 Checking for new articles...")

    for source_name, rss_url in SOURCES.items():

        print(f"\n📡 Source: {source_name}")

        try:

            feed = feedparser.parse(rss_url)

            if not feed.entries:

                print("❌ No news found.")

                continue

            new_count = 0

            for news in feed.entries[:MAX_NEWS_PER_SOURCE]:

                title = news.get(
                    "title",
                    "Untitled"
                )

                link = news.get(
                    "link",
                    ""
                )

                description = news.get(
                    "summary",
                    news.get(
                        "description",
                        ""
                    )
                )

                if not link:
                    continue

                # Skip already processed articles
                if news_exists(link):

                    print("⏭ Already processed:", title)

                    continue

                # Classify the article
                category, keywords = classify_news(
                    title,
                    description
                )

                print(f"{category}: {title}")

                if keywords:

                    print(
                        "   🔑 Keywords:",
                        ", ".join(keywords)
                    )

                # Extract image
                image_url = get_image(news)

                if image_url:

                    print("🖼 Image found")

                else:

                    print("📷 No image found")

                # Create Telegram message
                message = make_post(
                    title,
                    description
                )

                print("\n🆕 New article:")
                print(title)

                # Send to Telegram
                success = send_to_telegram(
                    message,
                    image_url
                )

                if success:

                    save_news(
                        link,
                        title
                    )

                    new_count += 1

                    print("💾 Article saved to database")

                    time.sleep(POST_DELAY)

            if new_count == 0:

                print("ℹ️ No new articles.")

            else:

                print(
                    f"✅ New articles published: {new_count}"
                )

        except Exception as error:

            print("❌ Source error:")
            print(error)


# ============================================================
# APPLICATION
# ============================================================

def main():

    print("🤖 News bot started!")

    print(
        "📡 Sources: Ukrainska Pravda, "
        "RBC-Ukraine, NV"
    )

    print("⏱ Checking every 5 minutes.")

    print("🧪 News classification is enabled.")

    print(
        "ℹ️ All new articles are currently published."
    )

    create_database()

    connection = sqlite3.connect("news.db")

    cursor = connection.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM published_news"
    )

    count = cursor.fetchone()[0]

    connection.close()

    if count == 0:

        initialize_existing_news()

    while True:

        try:

            check_news()

        except Exception as error:

            print("❌ General error:")
            print(error)

        print(
            "\n⏳ Next check in 5 minutes..."
        )

        time.sleep(CHECK_INTERVAL)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
