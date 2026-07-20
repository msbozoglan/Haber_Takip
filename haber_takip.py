import os
import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SENT_FILE = "sent_links.txt"
TITLE_FILE = "sent_titles.txt"

MAX_HABER = 20
MAX_YAS_SAAT = 720


def json_oku(dosya):
    with open(dosya, "r", encoding="utf-8") as f:
        return json.load(f)


KEYWORDS = json_oku("anahtarlar.json")
KAYNAKLAR = json_oku("kaynaklar.json")


def google_kaynaklari_olustur():

    kaynaklar = []

    siteler = [
        "lidergazete.com",
        "antalyakorfez.com",
        "antalyahakkinda.com",
        "antalyaekspres.com.tr",
        "gunhaber.com.tr",
        "antalyabulten.com",
        "antalyasonhaber.com",
        "akdenizgercek.com.tr",
        "yenialanya.com"
    ]

    for site in siteler:

        sorgu = " OR ".join([f'"{k}"' for k in KEYWORDS])
        sorgu = f"site:{site} ({sorgu})"

        rss = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(sorgu)}"
            "&hl=tr&gl=TR&ceid=TR:tr"
        )

        kaynaklar.append({
            "isim": f"Google {site}",
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
        timeout=15,
    )

    if r.status_code != 200:
        print("Telegram Hatası:", r.text)

    return r.status_code == 200

def web_sitesi_tara(isim, url):

    print(f"Web kontrol: {isim}")

    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )

        soup = BeautifulSoup(r.text, "lxml")

        bulunan = 0

        haberler = soup.select("a[href*='/antalya-gunlugu/']")

        for a in haberler:

            href = a.get("href", "")

            if not href:
                continue

            link = urljoin(url, href)

            baslik = a.get("title", "").strip()

            if not baslik:
                baslik = a.get_text(" ", strip=True)

            if len(baslik) < 10:
                continue
            if link in SENT:
                continue

            kelime = eslesen_kelime(baslik)

            if not kelime:
                continue

            mesaj = f"""📰 WEB HABERİ

🎯 {kelime}

📰 {baslik}

🌐 {isim}

🔗 {link}
"""

            if telegram_gonder(mesaj):
                SENT.add(link)
                bulunan += 1

        print(f"{isim}: {bulunan} web haberi bulundu")

    except Exception as e:
        print(f"{isim} web hatası:", e)

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

            LIMIT = 20 if "Google" in kaynak["isim"] else 15

            for item in feed.entries[:LIMIT]:
                
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

                mesaj = f"""📰 YENİ HABER

👤 Anahtar Kelime:
{kelime}

📰 Başlık:
{title}

🏢 Kaynak:
{kaynak["isim"]}

📅 Tarih:
{published}

📝 Açıklama:
{summary[:300]}

🔗 Haber Linki:
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
print("\nWeb siteleri taranıyor...\n")

web_sitesi_tara("Lider Gazete", "https://www.lidergazete.com")
web_sitesi_tara("Yeni Alanya", "https://www.yenialanya.com")
web_sitesi_tara("Ajansspor", "https://ajansspor.com")
web_sitesi_tara("Antalya Körfez", "https://www.antalyakorfez.com")
web_sitesi_tara("Antalya Ekspres", "https://www.antalyaekspres.com.tr")
web_sitesi_tara("Akdeniz Gerçek", "https://www.akdenizgercek.com.tr")
web_sitesi_tara("Gün Haber", "https://www.gunhaber.com.tr")
web_sitesi_tara("Antalya Hakkında", "https://www.antalyahakkinda.com")
    
    print(f"\nToplam {yeni} yeni haber gönderildi.")

if __name__ == "__main__":

    print("=" * 50)
    print("Haber Takip Sistemi Başlatıldı")
    print("=" * 50)

    haberleri_tara()

    print("=" * 50)
    print("İşlem tamamlandı.")
    print("=" * 50)
