import os
import json
import re
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
EVENT_FILE = "sent_events.txt"

MAX_HABER = 20
MAX_YAS_SAAT = 72


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
        "yenialanya.com", 
        "antalyamanset.com"
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

if os.path.exists(EVENT_FILE):
    with open(EVENT_FILE, "r", encoding="utf-8") as f:
        SENT_EVENTS = set(i.strip() for i in f if i.strip())
else:
    SENT_EVENTS = set()


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
    global yeni

    print(f"Web kontrol: {isim}")

    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20
        )

        soup = BeautifulSoup(r.text, "html.parser")

        bulunan = 0

        linkler = set()

        for a in soup.find_all("a", href=True):

            href = a["href"]

            if href.startswith("/"):
                href = urljoin(url, href)

            if not href.startswith("http"):
                continue

            if any(x in href.lower() for x in [
                "/haber/",
                "/makale/",
                "/antalya-gunlugu/",
                "/spor/",
                "/gundem/",
                "/ekonomi/"
            ]):
                linkler.add(href)

        for link in list(linkler)[:300]:

            if link in SENT:
                continue

            try:
                sayfa = requests.get(
                    link,
                    headers={"User-Agent":"Mozilla/5.0"},
                    timeout=15
                )

                s = BeautifulSoup(sayfa.text,"html.parser")

                if s.title:
                    baslik = s.title.get_text(" ", strip=True)
                else:
                    baslik = ""

                aciklama = ""

                if s.find("meta", attrs={"name": "description"}):
                    aciklama = s.find("meta", attrs={"name": "description"}).get("content", "")

                metin = baslik + " " + aciklama 

                # Aynı URL farklı şekilde gelirse tekrar gönderme
                link_normal = link.rstrip("/").lower()

                if any(x.rstrip("/").lower() == link_normal for x in SENT):
                    print("⛔ Daha önce gönderilmiş URL:", baslik)
                    continue

                # Aynı başlık farklı URL ile gelirse tekrar gönderme
                baslik_anahtari = haber_anahtari(baslik)

                if baslik_anahtari in SENT_TITLES:
                    print("⛔ Daha önce gönderilmiş başlık:", baslik)
                    continue

                # Aynı olay farklı başlık veya URL ile gelirse tekrar gönderme
                olay = olay_anahtari(baslik)

                if olay in SENT_EVENTS:
                    print("⛔ Daha önce gönderilmiş olay:", baslik)
                    continue

                if isim == "Antalya Manşet":
                    kelime = antalya_manset_eslesen_kelime(baslik, aciklama)
                else:
                    kelime = eslesen_kelime(metin)

                if not kelime:
                    continue

                mesaj=f"""📰 WEB HABERİ

🎯 {kelime}

📰 {baslik}

🌐 {isim}

🔗 {link}
"""

                if haber_anahtari(baslik) in SENT_TITLES:
                    continue

                if telegram_gonder(mesaj):
                    yeni += 1
                    print("Telegram'a gönderildi:", baslik)

                    SENT.add(link.rstrip("/"))
                    SENT_TITLES.add(haber_anahtari(baslik))
                    SENT_EVENTS.add(olay)

                    bulunan += 1

            except Exception:
                pass

        print(f"{isim}: {bulunan} web haberi bulundu")

    except Exception as e:
        print(e)

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

def haber_anahtari(baslik):
    baslik = temizle(baslik)
    baslik = re.sub(r'[^a-z0-9 ]', ' ', baslik)
    baslik = re.sub(r'\s+', ' ', baslik).strip()
    return baslik

def olay_anahtari(baslik):
    baslik = temizle(baslik)

    # Aynı olayın farklı başlıklarla gelmesini engellemek için
    if "200 bin euro" in baslik or "200 bin euroluk" in baslik:
        return "antalya sgk 200 bin euro rusvet kumpas"

    if "sgk" in baslik and "rusvet" in baslik and "antalyaspor" in baslik:
        return "antalya sgk rusvet antalyaspor"

    if "sgk" in baslik and "rusvet" in baslik and "tanriover" in baslik:
        return "antalya sgk rusvet tanriover"

    if "sgk" in baslik and "rusvet" in baslik and "kumpas" in baslik:
        return "antalya sgk rusvet kumpas"

    return haber_anahtari(baslik)

def eslesen_kelime(text):
    text = temizle(text)

    for kelime in KEYWORDS:
        if temizle(kelime) in text:
            return kelime

    return None

def antalya_manset_eslesen_kelime(baslik, metin):
    baslik = temizle(baslik)
    metin = temizle(metin)

    # Önce mevcut anahtar kelimeleri kontrol et
    for kelime in KEYWORDS:
        k = temizle(kelime)

        if k in baslik or k in metin:
            return kelime

    # Antalya Manşet için özel bağlam kontrolü
    sgk_kelimeleri = [
        "sgk",
        "sosyal güvenlik kurumu",
        "sosyal güvenlik",
        "sgk il müdürü",
        "sgk müdürü"
    ]

    kisi_kelimeleri = [
        "mehmet tanrıöver",
        "tanrıöver",
        "ali karaçallı",
        "ali karaçalı",
        "ali karacalı",
        "ali karacallı"
    ]

    olay_kelimeleri = [
        "rüşvet",
        "rüşvet soruşturması",
        "rüşvet davası",
        "rüşvet iddiası",
        "rüşvet operasyonu",
        "kumpas",
        "soruşturma",
        "iddianame",
        "200 bin euro",
        "200 bin euroluk"
    ]

    sgk_var = any(k in metin for k in sgk_kelimeleri)
    kisi_var = any(k in metin for k in kisi_kelimeleri)
    olay_var = any(k in metin for k in olay_kelimeleri)

    # SGK + kişi
    if sgk_var and kisi_var:
        return "SGK / ilgili kişi"

    # SGK + rüşvet/soruşturma bağlantısı
    if sgk_var and olay_var:
        return "SGK / ilgili soruşturma"

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

                if haber_anahtari(title) in SENT_TITLES:
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
                if haber_anahtari(title) in SENT_TITLES:
                    continue 
    
                if telegram_gonder(mesaj):
                    print("Telegram'a gönderildi.")

                    SENT.add(link)
                    SENT_TITLES.add(haber_anahtari(title))

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

    with open(EVENT_FILE, "w", encoding="utf-8") as f:
        for event in sorted(SENT_EVENTS):
            f.write(event + "\n")
            
    print("\nWeb siteleri taranıyor...\n")

    web_sitesi_tara("Lider Gazete", "https://www.lidergazete.com")
    web_sitesi_tara("Yeni Alanya", "https://www.yenialanya.com")
    web_sitesi_tara("Ajansspor", "https://ajansspor.com")
    web_sitesi_tara("Antalya Körfez", "https://www.antalyakorfez.com")
    web_sitesi_tara("Antalya Ekspres", "https://www.antalyaekspres.com.tr")
    web_sitesi_tara("Akdeniz Gerçek", "https://www.akdenizgercek.com.tr")
    web_sitesi_tara("Gün Haber", "https://www.gunhaber.com.tr")
    web_sitesi_tara("Antalya Hakkında", "https://www.antalyahakkinda.com")
    web_sitesi_tara("Antalya Son Haber", "https://www.antalyasonhaber.com")
    web_sitesi_tara("Antalya Gündem", "https://www.antalyagundem.com")
    web_sitesi_tara("Antalya Hürses", "https://www.antalyahurses.com")
    web_sitesi_tara("Antalya Bülten", "https://www.antalyabulten.com")
    web_sitesi_tara("Antalyam", "https://www.antalyam.com")
    web_sitesi_tara("Antalya Manşet", "https://antalyamanset.com")
    
    print(f"\nToplam {yeni} yeni haber gönderildi.")

if __name__ == "__main__":

    print("=" * 50)
    print("Haber Takip Sistemi Başlatıldı")
    print("=" * 50)

    haberleri_tara()

    print("=" * 50)
    print("İşlem tamamlandı.")
    print("=" * 50)
