import os
import json
import feedparser
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SENT_FILE = "sent_links.txt"


def json_oku(dosya):
    with open(dosya, "r", encoding="utf-8") as f:
        return json.load(f)


KEYWORDS = json_oku("anahtarlar.json")
KAYNAKLAR = json_oku("kaynaklar.json")
from urllib.parse import quote_plus

def google_kaynaklari_olustur():
    kaynaklar = []
    for kelime in KEYWORDS:
        rss = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus('\"' + kelime + '\"')}"
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

    return r.status_code == 200


def eslesen_kelime(text):

    text = text.lower()

    for kelime in KEYWORDS:

        if kelime.lower() in text:

            return kelime

    return None


tum_kaynaklar = {
    **KAYNAKLAR,
    "google_auto": google_kaynaklari_olustur()
}
def haberleri_tara():

    yeni = 0

    for grup in tum_kaynaklar.values():

        for kaynak in grup:

            print("Kontrol:", kaynak["isim"])

            try:

                feed = feedparser.parse(kaynak["rss"])

            except Exception as e:

                print(e)

                continue

            for item in feed.entries:

                title = item.get("title", "")

                summary = item.get("summary", "")

                link = item.get("link", "")

                published = item.get("published", "Tarih belirtilmemiş")

                if not link:

                    continue

                if link in SENT:

                    continue

                text = f"{title} {summary}"

                kelime = eslesen_kelime(text)

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

                    yeni += 1

                else:

                    print("Telegram gönderilemedi.")

    with open(SENT_FILE, "w", encoding="utf-8") as f:

        for link in sorted(SENT):

            f.write(link + "\n")

    print(f"\nToplam {yeni} yeni haber gönderildi.")


if __name__ == "__main__":

    print("=" * 50)
    print("Haber Takip Sistemi Başlatıldı")
    print("=" * 50)

    haberleri_tara()

    print("=" * 50)
    print("İşlem tamamlandı.")
    print("=" * 50)
