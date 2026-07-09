import os
import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SENT_FILE = "sent_links.txt"
TITLE_FILE = "sent_titles.txt"

MAX_HABER = 10
MAX_YAS_SAAT = 24


def json_oku(dosya):
    with open(dosya, "r", encoding="utf-8") as f:
        return json.load(f)


KEYWORDS = json_oku("anahtarlar.json")
KAYNAKLAR = json_oku("kaynaklar.json")


def google_kaynaklari_olustur():
    kaynaklar = []

    for kelime in KEYWORDS:
        sorgu = quote_plus(f'"{kelime}"')

        rss = (
            "https://news.google.com/rss/search?"
            f"q={sorgu}"
            "&hl=tr&gl=TR&ceid=TR:tr"
        )

        kaynaklar.append({
            "isim": f"Google Haberler ({kelime})",
            "rss": rss
        })

    return kaynaklar


if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        SENT = set(i.strip() for i in f if i.strip())
else:
    SENT = set()


if os.path.exists(TITLE_FILE):
    with open(TITLE_FILE, "r", encoding="utf-8") as f:
        SENT_TITLES = set(i.strip().lower() for i in f if i.strip())
else:
    SENT_TITLES = set()


def telegram_gonder(mesaj):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": mesaj,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    if r.status_code != 200:
        print("Telegram Hatası:", r.text)

    return r.status_code == 200

def temizle(metin):
    metin = metin.lower()

    degisim = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u"
    }

    for eski, yeni in degisim.items():
        metin = metin.replace(eski, yeni)

    return metin


def eslesen_kelime(text):
    text = temizle(text)

    for kelime in KEYWORDS:
        if temizle(kelime) in text:
            return kelime

    return None


def haber_yeni_mi(published):
    try:
        dt = parsedate_to_datetime(published)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return (
            datetime.now(timezone.utc) - dt
        ) <= timedelta(hours=MAX_YAS_SAAT)

    except Exception:
        return False


def haberleri_tara():
    yeni = 0
    gonderilen = 0

    tum_kaynaklar = {
        **KAYNAKLAR,
        "google_auto": google_kaynaklari_olustur()
    }

    for grup in tum_kaynaklar.values():
        for kaynak in grup:

            print("Kontrol:", kaynak["isim"])

            try:
                feed = feedparser.parse(kaynak["rss"])
                print("RSS Haber Sayısı:", len(feed.entries))
            except Exception as e:
                print("RSS Hatası:", e)
                continue

            for item in feed.entries:

                title = item.get("title", "").strip()
                summary = item.get("summary", "").strip()
                link = item.get("link", "").strip()
                published = item.get("published", "")

                if not link:
                    continue

                if link in SENT:
                    print("⛔ Daha önce gönderilmiş link:", title)
                    continue

                if title.lower() in SENT_TITLES:
                    print("⛔ Daha önce gönderilmiş başlık:", title)
                    continue

                if not haber_yeni_mi(published):
                    print("⛔ Eski haber:", title)
                    continue

                text = f"{title} {summary}"

                kelime = eslesen_kelime(text)

                if kelime:
                    print(f"✅ Eşleşme bulundu: {kelime}")

                if not kelime:
                    continue

                mesaj = f"""📰 Yeni Haber

🎯 Eşleşme:
{kelime}

📌 Başlık:
{title}

🌐 Kaynak:
{kaynak["isim"]}

📅 Tarih:
{published}

🔗 Link:
{link}
"""

                if telegram_gonder(mesaj):
                    print("Telegram'a gönderildi.")

                    SENT.add(link)
                    SENT_TITLES.add(title.lower())

                    yeni += 1
                    gonderilen += 1

                    if gonderilen >= MAX_HABER:
                        break
                else:
                    print("Telegram gönderilemedi.")

            if gonderilen >= MAX_HABER:
                break

        if gonderilen >= MAX_HABER:
            break

    with open(SENT_FILE, "w", encoding="utf-8") as f:
        for link in sorted(SENT):
            f.write(link + "\n")

    with open(TITLE_FILE, "w", encoding="utf-8") as f:
        for title in sorted(SENT_TITLES):
            f.write(title + "\n")

    print(f"\nToplam {yeni} yeni haber gönderildi.")

if __name__ == "__main__":

    print("=" * 50)
    print("Haber Takip Sistemi Başlatıldı")
    print("=" * 50)

    haberleri_tara()

    print("=" * 50)
    print("İşlem tamamlandı.")
    print("=" * 50)
