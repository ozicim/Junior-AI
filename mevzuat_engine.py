import re
import urllib.request
import time
import streamlit as st
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.generativeai as genai

# ============================================================
# 🔑 TÜRKÇEye ÖZGÜ SORUN: Python'da "GEÇİCİ".lower() → "geçi̇ci̇"
# Büyük İ harfi lower() ile "i̇" (noktalı i) üretir, "i" ile eşleşmez.
# Bu yüzden tüm tür tespitlerinde ASCII karşılıklarını kullanıyoruz.
#
# MADDE ID STANDARDI (Firebase döküman anahtarı):
#   Normal madde     → sadece numara          → "1", "86", "2A"
#   Geçici madde     → "GECİCİ_" + numara     → "GECİCİ_1", "GECİCİ_3"
#   Ek madde         → "EK_" + numara          → "EK_1", "EK_2"
#
# Alt çizgi (_) kullanmak prefix çakışmasını tamamen önler:
# "1" asla "GECİCİ_1" ile eşleşmez.
# ============================================================

YASAL_UYARI = (
    "⚠️ **Bilgi Amaçlıdır:** Bu madde metni Adalet Bakanlığı Mevzuat Bilgi "
    "Sistemi'nden alınmıştır. Güncel ve hukuken bağlayıcı metin için "
    "[mevzuat.gov.tr](https://www.mevzuat.gov.tr) adresini kontrol ediniz. "
    "JUNILEX hukuki danışmanlık hizmeti sunmamaktadır."
)


def _madde_turu_tespit(ham_metin: str) -> str:
    """
    Türkçe büyük/küçük harf sorununu bypass ederek
    madde türünü ASCII karşılıklarıyla tespit eder.
    Döndürür: 'gecici' | 'ek' | 'normal'
    """
    # ASCII'ye dönüştür: İ→I, Ş→S, Ç→C, Ğ→G, Ö→O, Ü→U
    ascii_map = str.maketrans("İĞÜŞÖÇığüşöç", "IGUSocigusoc")
    normalized = ham_metin.translate(ascii_map).lower()
    if "gecici" in normalized:
        return "gecici"
    if normalized.strip().startswith("ek ") or " ek madde" in normalized:
        return "ek"
    return "normal"


def _doc_id_uret(tur: str, asil_no: str) -> str:
    """
    Firebase döküman ID'sini standart ve çakışmasız üretir.
    Türkçe karakter içermez, alt çizgi prefix kullanır.
    """
    no = asil_no.strip().upper()
    if tur == "gecici":
        return f"GECİCİ_{no}"
    if tur == "ek":
        return f"EK_{no}"
    return no


def _kullanici_girisini_doc_id_cevir(girdi: str) -> list[str]:
    """
    Kullanıcının girdiği serbest metni olası Firebase ID'lerine çevirir.
    'geçici 1', 'Geçici 1', 'GEÇİCİ MADDE 1', '1' gibi her varyasyonu karşılar.
    Birden fazla ID döndürür çünkü eski veriler farklı formatlarda olabilir.
    """
    girdi = girdi.strip()
    tur = _madde_turu_tespit(girdi)

    # Sayısal kısmı çıkar
    sayi_match = re.search(r'(\d+[a-zA-Z]*)', girdi)
    if not sayi_match:
        # Sadece rakam girilmiş mi? Doğrudan kullan
        return [girdi.upper()]

    asil_no = sayi_match.group(1).upper()
    yeni_id = _doc_id_uret(tur, asil_no)

    # Eski formatlarda da arayabilmek için alternatif ID'ler ekle
    alternatifler = [yeni_id]
    if tur == "gecici":
        # Eski yüklemelerde "Geçici 1", "Geçi̇ci̇ 1" gibi olabilir
        alternatifler += [f"Geçici {asil_no}", f"GEÇİCİ {asil_no}", f"Geçi̇ci̇ {asil_no}"]
    elif tur == "ek":
        alternatifler += [f"Ek {asil_no}", f"EK {asil_no}"]
    else:
        # Normal madde için sadece numara — geçici/ek ile karışmaması için
        # hiçbir alternatif ekleme, sadece tam numara
        alternatifler = [asil_no]

    # Tekrarları kaldır, sırayı koru
    seen = set()
    return [x for x in alternatifler if not (x in seen or seen.add(x))]


class MevzuatBulutEngine:
    BASE_URL = "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={}&MevzuatTur=1&MevzuatTertip=5"
    db = None

    KANUNLAR = [
        {"id": "5237", "isim": "Türk Ceza Kanunu",        "kisaAd": "TCK",  "kategori": "Ceza Hukuku",     "aciklama": "Suç ve ceza kavramlarını düzenleyen temel kanun."},
        {"id": "5271", "isim": "Ceza Muhakemesi Kanunu",  "kisaAd": "CMK",  "kategori": "Ceza Hukuku",     "aciklama": "Ceza yargılaması usullerini düzenler."},
        {"id": "4721", "isim": "Türk Medeni Kanunu",      "kisaAd": "TMK",  "kategori": "Özel Hukuk",      "aciklama": "Kişiler, aile, miras ve eşya hukukunu kapsar."},
        {"id": "6098", "isim": "Türk Borçlar Kanunu",     "kisaAd": "TBK",  "kategori": "Özel Hukuk",      "aciklama": "Borç ilişkilerini ve sözleşmeleri kapsar."},
        {"id": "6102", "isim": "Türk Ticaret Kanunu",     "kisaAd": "TTK",  "kategori": "Ticaret Hukuku",  "aciklama": "Ticari işletme, şirketler ve kıymetli evrak hukuku."},
        {"id": "4857", "isim": "İş Kanunu",               "kisaAd": "İK",   "kategori": "İş Hukuku",       "aciklama": "İşçi ve işveren ilişkilerini düzenler."},
    ]

    @classmethod
    def get_kanunlar(cls):
        return cls.KANUNLAR

    @classmethod
    def veritabanini_baslat(cls):
        if not firebase_admin._apps:
            firebase_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_dict)
            firebase_admin.initialize_app(cred)
        if not cls.db:
            cls.db = firestore.client()

    @classmethod
    def madde_getir_buluttan(cls, kanun_kisa_adi, madde_no):
        """
        Kullanıcının girdiği madde_no'yu olası tüm Firebase ID formatlarına çevirir
        ve ilk bulunan dökümanı döndürür.
        Normal 'Madde 1' ile 'Geçici Madde 1' hiçbir koşulda karışmaz.
        """
        cls.veritabanini_baslat()

        aranacak_idler = _kullanici_girisini_doc_id_cevir(madde_no)

        maddeler_ref = (cls.db
                        .collection('kanunlar')
                        .document(kanun_kisa_adi)
                        .collection('maddeler'))

        for doc_id in aranacak_idler:
            doc = maddeler_ref.document(doc_id).get()
            if doc.exists:
                return doc.to_dict()

        # Bulunamadı — kullanıcıya yardımcı hata mesajı
        tur = _madde_turu_tespit(madde_no)
        if tur == "normal":
            ipucu = "Geçici madde için 'Geçici 1', ek madde için 'Ek 1' formatını kullanın."
        else:
            ipucu = "Normal madde için sadece rakam girin. Örn: '1', '86'."

        raise ValueError(
            f"'{kanun_kisa_adi}' içinde '{madde_no}' bulunamadı. "
            f"Denenen ID'ler: {aranacak_idler}. {ipucu} "
            f"Kanun daha önce yüklenmemişse Geliştirici Panelinden yükleyin."
        )

    @classmethod
    def kelime_ile_ara(cls, kanun_kisa_adi, arama_terimi):
        cls.veritabanini_baslat()
        arama_terimi = arama_terimi.lower()
        maddeler_ref = cls.db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler')
        docs = maddeler_ref.stream()

        sonuclar = []
        for doc in docs:
            veri = doc.to_dict()
            metin  = veri.get('metin', '').lower()
            baslik = veri.get('baslik', '').lower()
            if arama_terimi in metin or arama_terimi in baslik:
                sonuclar.append(veri)

        def siralama_anahtari(x):
            no = str(x.get('no', ''))
            # Geçici ve ek maddeler en sona
            if no.startswith('GECİCİ_') or no.startswith('EK_'):
                sayi = re.search(r'\d+', no)
                return (1, int(sayi.group()) if sayi else 0)
            return (0, int(no) if no.isdigit() else 0)

        return sorted(sonuclar, key=siralama_anahtari)

    @classmethod
    def madde_analiz_et(cls, api_key, madde_metni, kanun_adi, madde_no, soru=""):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            prompt = f"""
            Sen profesyonel bir hukuk asistanısın. Aşağıda metni verilen kanun maddesini bir hukukçu titizliğiyle analiz et.
            Kullanıcının özel sorusu varsa, analizini bu soruya odaklanarak yap.

            Kullanıcının Sorusu/Talebi: {soru}

            Analiz şunları içermelidir:
            1. Maddenin Özeti (Anlaşılır bir dil)
            2. Maddenin Koruduğu Hukuki Değer / Amacı
            3. Uygulamadaki Pratik Kritik Noktalar

            Kanun: {kanun_adi}
            Madde No: {madde_no}
            Madde Metni: {madde_metni}
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Analiz başarısız oldu: {str(e)}"

    @classmethod
    def kanunu_buluta_yukle(cls, kanun_id, kanun_kisa_adi, ozel_db=None):
        current_db = ozel_db if ozel_db else cls.db
        if not current_db:
            cls.veritabanini_baslat()
            current_db = cls.db

        url = cls.BASE_URL.format(kanun_id)
        st.info(f"🌍 [{kanun_kisa_adi}] Mevzuat sitesine bağlanılıyor...")

        try:
            html = ""
            for deneme in range(3):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Connection': 'keep-alive'
                    }
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=45) as response:
                        html = response.read().decode('utf-8')
                    break
                except Exception as e:
                    if deneme < 2:
                        st.warning(f"⏳ Site yavaş yanıt veriyor, {deneme + 2}. deneme yapılıyor...")
                        time.sleep(3)
                    else:
                        raise Exception(f"Mevzuat sitesi yanıt vermiyor: {str(e)}")

            current_db.collection('kanunlar').document(kanun_kisa_adi).set(
                {"isim": kanun_kisa_adi, "durum": "Aktif"}, merge=True
            )

            soup = BeautifulSoup(html, 'html.parser')
            metin_alani = soup.find(id="MevzuatMetin") or soup.find(id="MevzuatMetinBul") or soup

            for tag in metin_alani(["script", "style", "nav", "header", "footer", "button"]):
                tag.extract()
            for br in metin_alani.find_all("br"):
                br.replace_with("\n")
            for tag in metin_alani.find_all(["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                tag.insert_before("\n")
                tag.insert_after("\n")

            saf_metin = metin_alani.get_text(separator="\n", strip=True)
            saf_metin = saf_metin.replace('\xa0', ' ').replace('\r', '')
            saf_metin = re.sub(
                r'(?i)(?<!\n)((?:ek\s+|geçici\s+)?madde\s+[0-9]+[a-zçğıöşüA-Z/]*\s*[-\u2013\u2014])',
                r'\n\1', saf_metin
            )

            satirlar = saf_metin.split('\n')
            aktif_madde_no  = None
            aktif_madde_metni = []
            aktif_madde_baslik = ""
            kanun_ref = current_db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler')
            eklenen_madde_sayisi = 0

            for satir in satirlar:
                satir = satir.strip()
                if not satir:
                    continue

                match = re.search(
                    r'^\W*(ek\s+|geçici\s+)?madde\s*([0-9]+[a-zçğıöşüA-Z/]*)',
                    satir, re.IGNORECASE
                )

                if match:
                    # Önceki maddeyi kaydet
                    if aktif_madde_no:
                        kanun_ref.document(aktif_madde_no).set({
                            "no":     aktif_madde_no,
                            "baslik": aktif_madde_baslik,
                            "metin":  "\n\n".join(aktif_madde_metni)
                        })
                        eklenen_madde_sayisi += 1

                    # ✅ Türkçe-safe tür tespiti ve standart ID üretimi
                    on_ek_ham  = match.group(1) or ""
                    asil_no    = match.group(2).upper()
                    tur        = _madde_turu_tespit(on_ek_ham)
                    aktif_madde_no = _doc_id_uret(tur, asil_no)

                    # Başlık: tire/çizgiden sonraki kısım
                    parcalar = re.split(r'[-\u2013\u2014]', satir, maxsplit=1)
                    if len(parcalar) > 1:
                        aktif_madde_baslik = parcalar[1].strip()
                    else:
                        # Tür etiketini okunabilir göster
                        etiket = {"gecici": "Geçici ", "ek": "Ek ", "normal": ""}.get(tur, "")
                        aktif_madde_baslik = f"{etiket}Madde {asil_no}"

                    aktif_madde_metni = []

                elif aktif_madde_no:
                    aktif_madde_metni.append(satir)

            # Son maddeyi kaydet
            if aktif_madde_no:
                kanun_ref.document(aktif_madde_no).set({
                    "no":     aktif_madde_no,
                    "baslik": aktif_madde_baslik,
                    "metin":  "\n\n".join(aktif_madde_metni)
                })
                eklenen_madde_sayisi += 1

            if eklenen_madde_sayisi > 0:
                st.success(f"✅ BAŞARILI! {kanun_kisa_adi} için {eklenen_madde_sayisi} madde veritabanına yazıldı.")
                st.balloons()
            else:
                st.error(f"⚠️ {kanun_kisa_adi} için 0 madde bulundu! Site içeriği okunamadı.")

        except Exception as e:
            st.error(f"❌ Hata oluştu ({kanun_kisa_adi}): {str(e)}")
