import os
import json
import feedparser
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SENT_FILE = "sent_links.txt"
ANAHTAR_DOSYA = "anahtarlar.json"
KAYNAK_DOSYA = "kaynaklar.json"


def oku_json(dosya):
    with open(dosya, "r", encoding="utf-8") as f:
        return json.load(f)


KEYWORDS = oku_json(ANAHTAR_DOSYA)
KAYNAKLAR = oku_json(KAYNAK_DOSYA)


if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        sent = set(i.strip() for i in f if i.strip())
else:
    sent = set()


def telegram_gonder(mesaj):

    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": mesaj,
            "disable_web_page_preview": True
        },
        timeout=30
    )

    return r.status_code == 200


def eslesen_kelime(metin):

    metin = metin.lower()

    for kelime in KEYWORDS:
        if kelime.lower() in metin:
            return kelime

    return None
    
    def haberleri_tara():

    yeni = 0

    for grup_adi, grup in KAYNAKLAR.items():

        print(f"\n=== {grup_adi.upper()} ===")

        for kaynak in grup:

            print("Kontrol:", kaynak["isim"])

            try:

                feed = feedparser.parse(kaynak["rss"])

            except Exception as e:

                print("RSS okunamadı:", e)

                continue

            print(f"{len(feed.entries)} haber bulundu.")

            for item in feed.entries:

                title = item.get("title", "")
                link = item.get("link", "")
                summary = item.get("summary", "")
                published = item.get("published", "Tarih belirtilmemiş")

                if not link:
                    continue

                if link in sent:
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

                    print("Telegram gönderildi.")

                    sent.add(link)

                    yeni += 1

                else:

                    print("Telegram gönderilemedi.")

    with open(SENT_FILE, "w", encoding="utf-8") as f:

        for i in sorted(sent):

            f.write(i + "\n")

    print(f"\nToplam {yeni} yeni haber gönderildi.")
    if __name__ == "__main__":

    print("=" * 40)
    print("Haber Takip Sistemi Başlatıldı")
    print("=" * 40)

    haberleri_tara()

    print("=" * 40)
    print("İşlem tamamlandı.")
    print("=" * 40)
