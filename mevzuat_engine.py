import re
import urllib.request
import time
import streamlit as st
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.generativeai as genai


class MevzuatBulutEngine:
    # ✅ iframe URL'i kullan — ana sayfa içerik döndürmüyor
    BASE_URL = "https://www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?MevzuatTur=1&MevzuatNo={}&MevzuatTertip=5"
    db = None
    _analiz_model = None
    _configured_key = None

    KANUNLAR = [
        {"id": "5237", "isim": "Türk Ceza Kanunu",       "kisaAd": "TCK", "kategori": "Ceza Hukuku",    "aciklama": "Suç ve ceza kavramlarını düzenleyen temel kanun."},
        {"id": "5271", "isim": "Ceza Muhakemesi Kanunu", "kisaAd": "CMK", "kategori": "Ceza Hukuku",    "aciklama": "Ceza yargılaması usullerini düzenler."},
        {"id": "4721", "isim": "Türk Medeni Kanunu",     "kisaAd": "TMK", "kategori": "Özel Hukuk",     "aciklama": "Kişiler, aile, miras ve eşya hukukunu kapsar."},
        {"id": "6098", "isim": "Türk Borçlar Kanunu",    "kisaAd": "TBK", "kategori": "Özel Hukuk",     "aciklama": "Borç ilişkilerini ve sözleşmeleri kapsar."},
        {"id": "6102", "isim": "Türk Ticaret Kanunu",    "kisaAd": "TTK", "kategori": "Ticaret Hukuku", "aciklama": "Ticari işletme, şirketler ve kıymetli evrak hukuku."},
        {"id": "4857", "isim": "İş Kanunu",              "kisaAd": "İK",  "kategori": "İş Hukuku",      "aciklama": "İşçi ve işveren ilişkilerini düzenler."},
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
        if cls.db is None:
            cls.db = firestore.client()

    @classmethod
    def madde_getir_buluttan(cls, kanun_kisa_adi, madde_no):
        # db başlatılmamışsa başlat
        if cls.db is None:
            cls.veritabanini_baslat()

        # ✅ Önce session_state cache'ine bak — Firebase isteği yapmadan
        madde_id = (
            str(madde_no).strip().title()
            if "geçici" in str(madde_no).lower() or "ek" in str(madde_no).lower()
            else str(madde_no).strip().upper()
        )
        cache_key = f"madde_{kanun_kisa_adi}_{madde_id}"

        if cache_key in st.session_state:
            return st.session_state[cache_key]

        # Cache'de yoksa Firebase'den çek
        doc_ref = cls.db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler').document(madde_id)
        doc = doc_ref.get()
        if doc.exists:
            veri = doc.to_dict()
            st.session_state[cache_key] = veri  # Cache'e yaz
            return veri
        else:
            raise ValueError(f"'{kanun_kisa_adi}' içerisinde Madde {madde_id} bulunamadı.")

    @classmethod
    def kelime_ile_ara(cls, kanun_kisa_adi, arama_terimi):
        # ✅ Tüm kanunu session_state'te cache'le — aynı oturumda tekrar çekilmez
        cache_key = f"kanun_cache_{kanun_kisa_adi}"

        if cache_key not in st.session_state:
            maddeler_ref = cls.db.collection('kanunlar').document(kanun_kisa_adi).collection('maddeler')
            st.session_state[cache_key] = [doc.to_dict() for doc in maddeler_ref.stream()]

        terim = arama_terimi.lower()
        sonuclar = [
            m for m in st.session_state[cache_key]
            if terim in m.get('metin', '').lower() or terim in m.get('baslik', '').lower()
        ]
        return sorted(sonuclar, key=lambda x: int(x['no']) if str(x['no']).isdigit() else str(x['no']))

    @classmethod
    def _analiz_modeli_al(cls, api_key):
        """Analiz modelini cache'le — her analizde yeniden oluşturma."""
        if cls._configured_key != api_key:
            genai.configure(api_key=api_key)
            cls._configured_key = api_key
            cls._analiz_model = None

        if cls._analiz_model is None:
            cls._analiz_model = genai.GenerativeModel('models/gemini-2.5-flash')

        return cls._analiz_model

    @classmethod
    def madde_analiz_et(cls, api_key, madde_metni, kanun_adi, madde_no, soru=""):
        try:
            model = cls._analiz_modeli_al(api_key)

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

        # ✅ iframe URL — ana sayfa değil
        ana_url = f"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={kanun_id}&MevzuatTur=1&MevzuatTertip=5"
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
                        'Connection': 'keep-alive',
                        'Referer': ana_url,  # ✅ Referer şart
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
                        raise Exception(f"Mevzuat sitesi kilitli veya yanıt vermiyor: {str(e)}")

            current_db.collection('kanunlar').document(kanun_kisa_adi).set(
                {"isim": kanun_kisa_adi, "durum": "Aktif"}, merge=True
            )

            soup = BeautifulSoup(html, 'html.parser')

            for tag in soup(["script", "style", "nav", "header", "footer", "button"]):
                tag.extract()
            for br in soup.find_all("br"):
                br.replace_with("\n")
            for tag in soup.find_all(["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                tag.insert_before("\n")
                tag.insert_after("\n")

            saf_metin = soup.get_text(separator="\n", strip=True)
            saf_metin = saf_metin.replace('\xa0', ' ').replace('\r', '')
            saf_metin = re.sub(
                r'(?i)(?<!\n)((?:ek\s+|geçici\s+)?madde\s+[0-9]+[a-zçğıöşüA-Z/]*\s*[-\u2013\u2014])',
                r'\n\1',
                saf_metin
            )

            satirlar = saf_metin.split('\n')
            aktif_madde_no = None
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
                    if aktif_madde_no:
                        # ✅ "/" karakteri Firestore path ayracı — tire ile değiştir
                        guvenli_no = str(aktif_madde_no).replace("/", "-")
                        kanun_ref.document(guvenli_no).set({
                            "no": aktif_madde_no,
                            "baslik": aktif_madde_baslik,
                            "metin": "\n\n".join(aktif_madde_metni)
                        })
                        eklenen_madde_sayisi += 1

                    on_ek = match.group(1).strip().capitalize() + " " if match.group(1) else ""
                    asil_no = match.group(2).upper()
                    aktif_madde_no = f"{on_ek}{asil_no}".strip()

                    parcalar = re.split(r'[-\u2013\u2014]', satir, maxsplit=1)
                    aktif_madde_baslik = (
                        parcalar[1].strip() if len(parcalar) > 1
                        else f"{on_ek}Madde {asil_no}".strip()
                    )
                    aktif_madde_metni = []

                elif aktif_madde_no:
                    aktif_madde_metni.append(satir)

            if aktif_madde_no:
                guvenli_no = str(aktif_madde_no).replace("/", "-")
                kanun_ref.document(guvenli_no).set({
                    "no": aktif_madde_no,
                    "baslik": aktif_madde_baslik,
                    "metin": "\n\n".join(aktif_madde_metni)
                })
                eklenen_madde_sayisi += 1

            if eklenen_madde_sayisi > 0:
                st.success(f"✅ BAŞARILI! {kanun_kisa_adi} için toplam {eklenen_madde_sayisi} madde veritabanına yazıldı.")
                st.balloons()
            else:
                st.error(f"⚠️ DİKKAT: {kanun_kisa_adi} için 0 madde bulundu!")

        except Exception as e:
            st.error(f"❌ Hata oluştu ({kanun_kisa_adi}): {str(e)}")
