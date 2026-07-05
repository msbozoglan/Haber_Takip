import feedparser
import requests
import os

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

RSS_URL = (
    "https://news.google.com/rss/search?"
    "q=%22Ali+Kara%C3%A7al%C4%B1%22+OR+%22Ali+Karacal%C4%B1%22+OR+%22Ali+Kara%C3%A7all%C4%B1%22+OR+%22Ali+Karacall%C4%B1%22"
    "+OR+Antalya+SGK+OR+%22Sosyal+G%C3%BCvenlik+Kurumu+Antalya%22+OR+Antalya"
    "&hl=tr&gl=TR&ceid=TR:tr"
)
KEYWORDS = [
    "Ali Karaçalı",
    "Ali Karacalı",
    "Ali Karaçallı",
    "Ali Karacallı",
    "Mehmet Tanrıöver", 
    "Antalya Sgk",
    "Antalya Sosyal Güvenlik İl Müdürlüğü", 
    "Sgk Antalya", 
]

SENT_FILE = "sent_links.txt"

# Daha önce gönderilen linkleri oku
if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        sent = set(line.strip() for line in f if line.strip())
else:
    sent = set()

print("Google Haberler kontrol ediliyor...")
new_count = 0
feed = feedparser.parse(RSS_URL)

print(f"{len(feed.entries)} haber bulundu.")

for item in feed.entries:

    title = item.get("title", "")
    link = item.get("link", "")
    summary = item.get("summary", "")
    published = item.get("published", "Tarih belirtilmemiş")

    source_name = "Google Haberler"
    if "source" in item:
        try:
            source_name = item.source.title
        except Exception:
            pass

    text = f"{title} {summary}"

    # keyword filtre
    if not any(k.lower() in text.lower() for k in KEYWORDS):
        continue

    # daha önce gönderildiyse atla
    if link in sent:
        continue

    message = f"""📰 Ali Karaçallı ile ilgili yeni haber

📌 Başlık:
{title}

🌐 Kaynak:
{source_name}

📅 Tarih:
{published}

🔗 Haber:
{link}
"""

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    print("Telegram:", response.status_code)

    if response.status_code == 200:
        sent.add(link)
        new_count += 1

# Gönderilen linkleri kaydet
with open(SENT_FILE, "w", encoding="utf-8") as f:
    for link in sorted(sent):
        f.write(link + "\n")

print(f"{new_count} yeni haber Telegram'a gönderildi.")
print("İşlem tamamlandı.")
