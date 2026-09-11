import feedparser
import requests

RSS_URL = "https://www.pravda.com.ua/rss/"


def ask_ai(title, description):

    prompt = f"""
Ти редактор українського новинного Telegram-каналу.

Твоє завдання — зробити короткий новинний текст на основі
ВИКЛЮЧНО інформації, яка наведена нижче.

Суворі правила:
- не вигадуй жодних фактів;
- не додавай інформацію, якої немає в тексті;
- не змінюй цифри, імена, назви та факти;
- не роби припущень;
- не використовуй фрази на кшталт "за останні дні", якщо цього немає в джерелі;
- 2–4 короткі речення;
- українська мова;
- нейтральний новинний стиль;
- без власних висновків.

ЗАГОЛОВОК:
{title}

ТЕКСТ:
{description}

Напиши лише готовий текст новини.
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen3:4b",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    if response.status_code != 200:
        print("❌ Помилка Ollama:")
        print(response.text)
        return None

    data = response.json()

    return data.get("response", "").strip()


print("📡 Отримуємо новини з RSS...")

feed = feedparser.parse(RSS_URL)

if not feed.entries:
    print("❌ RSS не повернув новин.")
    exit()

news = feed.entries[0]

title = news.get("title", "Без заголовка")
description = news.get(
    "summary",
    news.get("description", "")
)

print("\n==============================")
print("ОРИГІНАЛ")
print("==============================")

print("📰", title)
print("\n", description)

print("\n🤖 Qwen обробляє новину...")
print("⏳ Це може зайняти деякий час.")

result = ask_ai(title, description)

if result:

    print("\n==============================")
    print("ГОТОВИЙ ТЕКСТ")
    print("==============================")

    print(result)

print("\n✅ Тест завершено.")