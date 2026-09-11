import feedparser

SOURCES = {
    "Українська правда": "https://www.pravda.com.ua/rss/",
    "РБК-Україна": "https://www.rbc.ua/static/rss/all.ukr.rss.xml",
    "NV": "https://nv.ua/ukr/rss/all.xml"
}

for source_name, rss_url in SOURCES.items():

    print("\n==============================")
    print(source_name)
    print(rss_url)
    print("==============================")

    feed = feedparser.parse(rss_url)

    print("Новостей:", len(feed.entries))

    for news in feed.entries[:3]:
        print("📰", news.get("title"))
        print("🔗", news.get("link"))