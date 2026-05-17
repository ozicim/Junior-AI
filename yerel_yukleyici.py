"""
JUNILEX - Yerel Kanun Yükleyici (v2 - iframe Fix)
==================================================
Kendi bilgisayarında çalıştır, Firebase'e yazar.

Kullanım:
    pip install firebase-admin beautifulsoup4
    python yerel_yukleyici.py
"""

import re
import time
import urllib.request
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore

FIREBASE_JSON_YOLU = "kilit.json"
BEKLEME_SURESI = 2

KANUNLAR = [
    ("5237", "TCK", "Türk Ceza Kanunu"),
    ("5271", "CMK", "Ceza Muhakemesi Kanunu"),
    ("4721", "TMK", "Türk Medeni Kanunu"),
    ("6098", "TBK", "Türk Borçlar Kanunu"),
    ("6102", "TTK", "Türk Ticaret Kanunu"),
    ("4857", "İK", "İş Kanunu"),
]

# ✅ DÜZELTME: Ana sayfa değil iframe URL'i
IFRAME_URL = "https://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?MevzuatTur=1&MevzuatNo={}&MevzuatTertip=5"


def firebase_baslat():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_JSON_YOLU)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def kanunu_yukle(db, kanun_id, kanun_kisa_adi, kanun_tam_adi):
    url = IFRAME_URL.format(kanun_id)
    ana_url = f"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={kanun_id}&MevzuatTur=1&MevzuatTertip=5"

    print(f"\n{'='*60}")
    print(f"▶ [{kanun_kisa_adi}] {kanun_tam_adi}")
    print(f"{'='*60}")

    html = ""
    for deneme in range(3):
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9",
                "Referer": ana_url,  # ✅ Referer şart - site kontrol ediyor
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as resp:
                html = resp.read().decode("utf-8")
            print(f"  ✅ HTML indirildi ({len(html):,} karakter)")
            break
        except Exception as e:
            if deneme < 2:
                print(f"  ⚠️  Deneme {deneme+1} başarısız, bekleniyor... ({e})")
                time.sleep(BEKLEME_SURESI + 2)
            else:
                print(f"  ❌ HATA: {e}")
                return 0

    madde_sayisi = html.lower().count("madde")
    print(f"  📊 'madde' kelimesi: {madde_sayisi} kez")
    if madde_sayisi == 0:
        print(f"  ❌ İçerik boş, atlanıyor.")
        return 0

    # --- PARSE ---
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "button"]):
        tag.extract()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(
        ["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]
    ):
        tag.insert_before("\n")
        tag.insert_after("\n")

    saf_metin = soup.get_text(separator="\n", strip=True)
    saf_metin = saf_metin.replace("\xa0", " ").replace("\r", "")
    saf_metin = re.sub(
        r"(?i)(?<!\n)((?:ek\s+|geçici\s+)?madde\s+[0-9]+[a-zçğıöşüA-Z/]*\s*[-\u2013\u2014])",
        r"\n\1",
        saf_metin,
    )

    satirlar = saf_metin.split("\n")
    aktif_madde_no = None
    aktif_madde_metni = []
    aktif_madde_baslik = ""
    eklenen = 0

    db.collection("kanunlar").document(kanun_kisa_adi).set(
        {"isim": kanun_tam_adi, "kisaAd": kanun_kisa_adi, "durum": "Aktif"},
        merge=True,
    )
    kanun_ref = (
        db.collection("kanunlar").document(kanun_kisa_adi).collection("maddeler")
    )

    for satir in satirlar:
        satir = satir.strip()
        if not satir:
            continue

        match = re.search(
            r"^\W*(ek\s+|geçici\s+)?madde\s*([0-9]+[a-zçğıöşüA-Z/]*)",
            satir,
            re.IGNORECASE,
        )

        if match:
            if aktif_madde_no:
                guvenli_no = str(aktif_madde_no).replace("/", "-")
                kanun_ref.document(guvenli_no).set(
                    {
                        "no": aktif_madde_no,  # no alanında orijinal hali kalabilir
                        "baslik": aktif_madde_baslik,
                        "metin": "\n\n".join(aktif_madde_metni),
                    }
                )
                eklenen += 1
                if eklenen % 50 == 0:
                    print(f"  📝 {eklenen} madde yazıldı...")

            on_ek = match.group(1).strip().capitalize() + " " if match.group(1) else ""
            asil_no = match.group(2).upper()
            aktif_madde_no = f"{on_ek}{asil_no}".strip()

            parcalar = re.split(r"[-\u2013\u2014]", satir, maxsplit=1)
            aktif_madde_baslik = (
                parcalar[1].strip()
                if len(parcalar) > 1
                else f"{on_ek}Madde {asil_no}".strip()
            )
            aktif_madde_metni = []

        elif aktif_madde_no:
            aktif_madde_metni.append(satir)

    if aktif_madde_no:
        guvenli_no = str(aktif_madde_no).replace("/", "-")
        kanun_ref.document(guvenli_no).set(
            {
                "no": aktif_madde_no,  # no alanında orijinal hali kalabilir
                "baslik": aktif_madde_baslik,
                "metin": "\n\n".join(aktif_madde_metni),
            }
        )
        eklenen += 1

    if eklenen > 0:
        print(f"  ✅ TAMAMLANDI: {eklenen} madde Firebase'e yazıldı.")
    else:
        print(f"  ⚠️  0 madde bulundu! Regex tutmadı.")

    return eklenen


if __name__ == "__main__":
    print("\n🔥 JUNILEX Yerel Kanun Yükleyici v2 Başlatılıyor...")

    try:
        db = firebase_baslat()
        print("✅ Firebase bağlantısı kuruldu.\n")
    except Exception as e:
        print(f"❌ Firebase bağlantısı başarısız: {e}")
        print("   kilit.json bu klasörde olmalı.")
        exit(1)

    toplam = 0
    basarisiz = []

    for kanun_id, kisa_ad, tam_ad in KANUNLAR:
        eklenen = kanunu_yukle(db, kanun_id, kisa_ad, tam_ad)
        toplam += eklenen
        if eklenen == 0:
            basarisiz.append(kisa_ad)
        time.sleep(BEKLEME_SURESI)

    print(f"\n{'='*60}")
    print(f"📊 GENEL ÖZET")
    print(f"{'='*60}")
    print(f"   Toplam yazılan madde : {toplam}")
    print(f"   Başarılı kanun       : {len(KANUNLAR) - len(basarisiz)}/{len(KANUNLAR)}")
    if basarisiz:
        print(f"   Başarısız olanlar    : {', '.join(basarisiz)}")
    else:
        print(f"   🎉 Tüm kanunlar başarıyla yüklendi!")
