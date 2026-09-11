import feedparser
import requests
import sqlite3
import time
import re
from html import unescape


# ============================================================
# НАСТРОЙКИ
# ============================================================

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@holovni_novyny_ua"

SOURCES = {
    "Українська правда": "https://www.pravda.com.ua/rss/",
    "РБК-Україна": "https://www.rbc.ua/static/rss/all.ukr.rss.xml",
    "NV": "https://nv.ua/ukr/rss/all.xml"
}

CHECK_INTERVAL = 300
POST_DELAY = 5
MAX_NEWS_PER_SOURCE = 10


# ============================================================
# КЛЮЧЕВЫЕ СЛОВА ДЛЯ ФИЛЬТРА
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
# ОЧИСТКА ТЕКСТА
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# ФИЛЬТР НОВОСТЕЙ
# ============================================================

def classify_news(title, description):
    text = clean_text(f"{title} {description}").lower()

    score = 0
    matched_keywords = []

    # Сильные слова = 3 балла
    for keyword in STRONG_KEYWORDS:
        if keyword.lower() in text:
            score += 3
            matched_keywords.append(f"{keyword} (+3)")

    # Средние слова = 2 балла
    for keyword in MEDIUM_KEYWORDS:

        keyword_lower = keyword.lower()

        # Не считаем погодный фронт
        if keyword_lower == "фронт":
            if any(excluded in text for excluded in EXCLUDED_PHRASES):
                continue

        if keyword_lower in text:
            score += 2
            matched_keywords.append(f"{keyword} (+2)")

    # Слабые слова = 1 балл
    for keyword in WEAK_KEYWORDS:
        if keyword.lower() in text:
            score += 1
            matched_keywords.append(f"{keyword} (+1)")

    # 3 балла и больше = важная новость
    if score >= 3:
        return "🔴 ВАЖНО", matched_keywords

    return "🟡 ОБЫЧНАЯ", matched_keywords


# ============================================================
# HTML ДЛЯ TELEGRAM
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
# РАБОТА С БАЗОЙ ДАННЫХ
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
# ПОИСК ФОТО
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
# ОТПРАВКА В TELEGRAM
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

            print("✅ Опубликовано")

            return True

        elif response.status_code == 429:

            print("⚠️ Telegram временно ограничил отправку")

            try:
                retry_after = response.json()["parameters"]["retry_after"]

            except:
                retry_after = 60

            print(f"⏳ Ждём {retry_after} секунд...")

            time.sleep(retry_after)

            return False

        else:

            print("❌ Ошибка Telegram:")
            print(response.text)

            return False

    except Exception as error:

        print("❌ Ошибка соединения:")
        print(error)

        return False


# ============================================================
# ПЕРВЫЙ ЗАПУСК
# ============================================================

def initialize_existing_news():

    print("\n📚 Первый запуск: запоминаем существующие новости...")

    total = 0

    for source_name, rss_url in SOURCES.items():

        print(f"\n📡 {source_name}")

        try:

            feed = feedparser.parse(rss_url)

            if not feed.entries:

                print("❌ Новости не найдены")

                continue

            for news in feed.entries[:MAX_NEWS_PER_SOURCE]:

                link = news.get("link", "")
                title = news.get("title", "Без заголовка")

                if not link:
                    continue

                if not news_exists(link):

                    save_news(link, title)

                    total += 1

                    print("📌 Запомнено:", title)

        except Exception as error:

            print("❌ Ошибка источника:")
            print(error)

    print(f"\n✅ Запомнено старых новостей: {total}")
    print("ℹ️ Старые новости публиковаться не будут.")


# ============================================================
# ПРОВЕРКА НОВОСТЕЙ
# ============================================================

def check_news():

    print("\n🔎 Проверяем новости...")

    for source_name, rss_url in SOURCES.items():

        print(f"\n📡 Источник: {source_name}")

        try:

            feed = feedparser.parse(rss_url)

            if not feed.entries:

                print("❌ Новости не найдены.")

                continue

            new_count = 0

            for news in feed.entries[:MAX_NEWS_PER_SOURCE]:

                title = news.get(
                    "title",
                    "Без заголовка"
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

                # Уже была опубликована
                if news_exists(link):

                    print("⏭ Уже опубликовано:", title)

                    continue

                # Определяем важность
                category, keywords = classify_news(
                    title,
                    description
                )

                print(f"{category}: {title}")

                if keywords:

                    print(
                        "   🔑 Ключевые слова:",
                        ", ".join(keywords)
                    )

                # Ищем фото
                image_url = get_image(news)

                if image_url:

                    print("🖼 Фото найдено")

                else:

                    print("📷 Фото не найдено")

                # Создаём сообщение
                message = make_post(
                    title,
                    description
                )

                print("\n🆕 Новая новость:")
                print(title)

                # Отправляем
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

                    print("💾 Новость сохранена в базе")

                    time.sleep(POST_DELAY)

            if new_count == 0:

                print("ℹ️ Новых новостей нет.")

            else:

                print(
                    f"✅ Опубликовано новых: {new_count}"
                )

        except Exception as error:

            print("❌ Ошибка источника:")
            print(error)


# ============================================================
# ЗАПУСК БОТА
# ============================================================

def main():

    print("🤖 Новинний бот запущено!")

    print(
        "📡 Источники: Українська правда, "
        "РБК-Україна, NV"
    )

    print("⏱ Проверка каждые 5 минут.")

    print("🧪 Фильтр работает в тестовом режиме.")

    print(
        "ℹ️ Все новости пока продолжают публиковаться."
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

            print("❌ Общая ошибка:")
            print(error)

        print(
            "\n⏳ Следующая проверка через 5 минут..."
        )

        time.sleep(CHECK_INTERVAL)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()