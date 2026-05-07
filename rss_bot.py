import feedparser
import requests
import csv
import json
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    })

def main():
    seen = load_seen()
    new_seen = set()
    all_news = []

    with open("feeds.csv") as f:
        reader = csv.DictReader(f)
        feeds = list(reader)

    for row in feeds:
        sottostante = row["Sottostante"]
        ticker = row["Ticker"]
        url = row["RSS_URL"]

        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:  # max 5 news per feed
            guid = entry.get("id") or entry.get("link", "")
            if not guid or guid in seen:
                continue
            new_seen.add(guid)
            all_news.append({
                "sottostante": sottostante,
                "ticker": ticker,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })

    if all_news:
        # Raggruppa per sottostante
        grouped = {}
        for n in all_news:
            key = f"{n['sottostante']} ({n['ticker']})"
            grouped.setdefault(key, []).append(n)

        for sottostante, news_list in grouped.items():
            msg = f"<b>{sottostante}</b>\n"
            for n in news_list:
                msg += f"• <a href='{n['link']}'>{n['title']}</a>\n"
            send_telegram(msg)

    seen.update(new_seen)
    # Mantieni solo gli ultimi 5000 guid per non far crescere il file
    if len(seen) > 5000:
        seen = set(list(seen)[-5000:])
    save_seen(seen)
    print(f"Nuove news trovate: {len(all_news)}")

if __name__ == "__main__":
    main()
