import feedparser
import requests
import os

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

RSS_URL = (
    "https://news.google.com/rss/search?"
    "q=(%22Ali+Kara%C3%A7al%C4%B1%22+OR+%22Ali+Karacal%C4%B1%22+OR+%22Ali+Kara%C3%A7all%C4%B1%22+OR+%22Ali+Karacall%C4%B1%22)"
    "&hl=tr&gl=TR&ceid=TR:tr"
)
)
KEYWORDS = [
    "Ali Karaçalı",
    "Ali Karacalı",
    "Ali Karaçallı",
    "Ali Karacallı",
]

SENT_FILE = "sent_links.txt"

if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        sent = set(line.strip() for line in f)
else:
    sent = set()

feed = feedparser.parse(RSS_URL)

for item in feed.entries:
    title = item.title
    link = item.link
    summary = getattr(item, "summary", "")

    text = f"{title} {summary}"

    if any(k.lower() in text.lower() for k in KEYWORDS):

        if link in sent:
            continue

        message = f"""📰 Yeni Haber

{title}

{link}
"""

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": message
            }
        )

        sent.add(link)

with open(SENT_FILE, "w", encoding="utf-8") as f:
    for i in sent:
        f.write(i + "\n")
requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": "✅ Haber takip sistemi başarıyla çalışıyor."
    }
)
