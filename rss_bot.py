import feedparser
import requests
import csv
import json
import os
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen.json"
HOURS_BACK = 7  # un'ora di margine rispetto al cron da 6h

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def is_recent(entry):
    try:
        published = entry.get("published", "")
        if not published:
            return True
        dt = parsedate_to_datetime(published)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - dt < timedelta(hours=HOURS_BACK)
    except Exception:
        return True

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

        try:
            feed = feedparser.parse(url)
        except Exception:
            continue

        for entry in feed.entries[:3]:
            guid = entry.get("id") or entry.get("link", "")
            if not guid or guid in seen:
                continue
            if not is_recent(entry):
                new_seen.add(guid)  # marca come visto ma non mandare
                continue
            new_seen.add(guid)
            all_news.append({
                "sottostante": sottostante,
                "ticker": ticker,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
            })

    if all_news:
        all_news = all_news[:20]
        msg = f"<b>News ultimi 6h ({len(all_news)})</b>\n\n"
        for n in all_news:
            msg += f"<b>{n['ticker']}</b> — <a href='{n['link']}'>{n['title']}</a>\n"
        send_telegram(msg)
    else:
        print("Nessuna news recente.")

    seen.update(new_seen)
    if len(seen) > 5000:
        seen = set(list(seen)[-5000:])
    save_seen(seen)
    print(f"Nuove news trovate: {len(all_news) if all_news else 0}")

if __name__ == "__main__":
    main()
