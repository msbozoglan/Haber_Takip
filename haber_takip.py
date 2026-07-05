import feedparser
import requests
import os

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

RSS_URL = "https://news.google.com/rss/search?q=Ali+Karaçalı+OR+Ali+Karacalı+OR+Karaçalı+OR+Karacalı&hl=tr&gl=TR&ceid=TR:tr"

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

import json
import logging
import os
import hashlib
from datetime import datetime

import feedparser

# Dosya yolları
KAYNAKLAR_DOSYASI = "kaynaklar.json"
HABERLER_DOSYASI = "haberler.json"
OKUNAN_DOSYASI = "okunan_haberler.json"
LOG_DOSYASI = "sistem.log"

# Log ayarları
logging.basicConfig(
    filename=LOG_DOSYASI,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def dosya_oku(dosya, varsayilan):
    if not os.path.exists(dosya):
        return varsayilan

    with open(dosya, "r", encoding="utf-8") as f:
        return json.load(f)


def dosya_yaz(dosya, veri):
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)


def haber_id(link):
    return hashlib.md5(link.encode()).hexdigest()


def rss_oku(url):
    try:
        return feedparser.parse(url)
    except Exception as e:
        logging.error(f"RSS okunamadı: {url} - {e}")
        return None


def haberleri_topla():

    kaynaklar = dosya_oku(KAYNAKLAR_DOSYASI, {})

    okunan = set(dosya_oku(OKUNAN_DOSYASI, []))

    yeni_haberler = []

    for kategori in kaynaklar.values():

        for kaynak in kategori:

            print(f"Taranıyor: {kaynak['isim']}")

            feed = rss_oku(kaynak["rss"])

            if not feed:
                continue

            for haber in feed.entries:

                link = haber.get("link", "")

                hid = haber_id(link)

                if hid in okunan:
                    continue

                veri = {
                    "id": hid,
                    "kaynak": kaynak["isim"],
                    "baslik": haber.get("title", ""),
                    "link": link,
                    "tarih": haber.get("published", ""),
                    "ozet": "",
                    "kategori": "",
                    "onem": ""
                }

                yeni_haberler.append(veri)
                okunan.add(hid)

    dosya_yaz(HABERLER_DOSYASI, yeni_haberler)
    dosya_yaz(OKUNAN_DOSYASI, list(okunan))

    print(f"{len(yeni_haberler)} yeni haber bulundu.")


if __name__ == "__main__":
    print("Haber Takip Sistemi Başlatıldı")
    haberleri_topla()
    print("İşlem tamamlandı.")
