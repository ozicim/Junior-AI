import re
import urllib.request
import time
import requests
import streamlit as st
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.generativeai as genai

# ==========================================
# ⚖️ HUKUKİ SORUMLULUK UYARISI (sabit metin)
# ==========================================
YASAL_UYARI = (
    "⚠️ **Bilgi Amaçlıdır:** Bu madde metni Adalet Bakanlığı Mevzuat Bilgi "
    "Sistemi'nden alınmıştır. Güncel ve hukuken bağlayıcı metin için "
    "[mevzuat.gov.tr](https://www.mevzuat.gov.tr) adresini kontrol ediniz. "
    "JUNILEX hukuki danışmanlık hizmeti sunmamaktadır."
)


# ==========================================
# 🌐 BEDESTEN API İSTEMCİSİ
# ==========================================
class BedestenAPI:
    """
    Adalet Bakanlığı'nın resmi Bedesten arama altyapısına erişim sağlar.
    mevzuat.gov.tr'yi kazımak yerine resmi endpoint'leri kullanır.
    Kaynak: github.com/saidsurucu/mevzuat-mcp (MIT Lisanslı)
    """

    # Adalet Bakanlığı'nın Solr tabanlı arama servisi
    ARAMA_URL = "https://bedesten.adalet.gov.tr/mevzuat/aralik-ara"
    DETAY_URL = "https://bedesten.adalet.gov.tr/mevzuat"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; JUNILEX/2.0)",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin":  "https://mevzuat.gov.tr",
        "Referer": "https://mevzuat.gov.tr/",
    }

    # Bilinen ana kanunların Bedesten mevzuat numaraları
    # Format: kanun_kisa_adi -> (mevzuat_no, mevzuat_tur)
    KANUN_MAP = {
        "TCK":  ("5237", "KANUN"),
        "CMK":  ("5271", "KANUN"),
        "TMK":  ("4721", "KANUN"),
        "TBK":  ("6098", "KANUN"),
        "TTK":  ("6102", "KANUN"),
        "İK":   ("4857", "KANUN"),
        "İİK":  ("2004", "KANUN"),
        "SPK":  ("6362", "KANUN"),
        "AY":   ("2709", "KANUN"),
        "İYUK": ("2577", "KANUN"),
        "SGSK": ("5510", "KANUN"),
        "YUKK": ("6458", "KANUN"),
    }

    @classmethod
    def _kanun_no_al(cls, kanun_kisa_adi: str) -> tuple:
        return cls.KANUN_MAP.get(kanun_kisa_adi, (None, "KANUN"))

    @classmethod
    def madde_ara(cls, kanun_kisa_adi: str, madde_no: str) -> dict | None:
        """
        Bedesten'in madde arama endpoint'iyle belirli bir maddeyi getirir.
        """
        kanun_no, mevzuat_tur = cls._kanun_no_al(kanun_kisa_adi)
        if not kanun_no:
            return None

        madde_no_temiz = str(madde_no).strip()
        # Bedesten madde arama payload'ı
        payload = {
            "mevzuatNo": kanun_no,
            "mevzuatTur": mevzuat_tur,
            "mevzuatTertip": "5",
            "keyword": f"madde {madde_no_temiz}",
            "caseSensitive": False,
            "maxResults": 20
        }
        try:
            r = requests.post(
                "https://bedesten.adalet.gov.tr/mevzuat/madde-ara",
                json=payload,
                headers=cls.HEADERS,
                timeout=15
            )
            if r.status_code != 200:
                return None
            veri = r.json()
            maddeler = veri.get("data", []) or veri.get("maddeler", []) or []

            for m in maddeler:
                m_no_ham = str(m.get("maddeNo", m.get("madde_numarasi", ""))).strip()
                m_no_temiz2 = m_no_ham.upper().replace("MADDE", "").strip()
                if m_no_temiz2 == madde_no_temiz.upper():
                    return {
                        "no":     madde_no_temiz.upper(),
                        "baslik": m.get("baslik", m.get("madde_numarasi", f"Madde {madde_no_temiz}")),
                        "metin":  m.get("metin", m.get("text", "Madde metni bulunamadı."))
                    }
            return None
        except Exception:
            return None

    @classmethod
    def kanun_tam_liste(cls, kanun_kisa_adi: str) -> list:
        """
        Bir kanunun tüm maddelerini Bedesten API'sinden çeker.
        Geliştirici toplu yükleme paneli için kullanılır.
        """
        kanun_no, mevzuat_tur = cls._kanun_no_al(kanun_kisa_adi)
        if not kanun_no:
            return []
        try:
            payload = {
                "mevzuatNo": kanun_no,
                "mevzuatTur": mevzuat_tur,
                "mevzuatTertip": "5"
            }
            r = requests.post(
                "https://bedesten.adalet.gov.tr/mevzuat/madde-listesi",
                json=payload,
                headers=cls.HEADERS,
                timeout=30
            )
            if r.status_code != 200:
                return []
            veri = r.json()
            return veri.get("data", []) or veri.get("maddeler", [])
        except Exception:
            return []


# ==========================================
# 🏛️ ANA MEVZUAT ENGINE (HİBRİT)
# ==========================================
class MevzuatBulutEngine:
    """
    Öncelik sırası:
      1. Bedesten API — Adalet Bakanlığı'nın resmi endpoint'i, anlık, scraping yok
      2. Firebase cache — Daha önce yüklenmiş maddeler
      3. mevzuat.gov.tr scraping — Son çare (IP engeli riski var)
    """

    BASE_URL = "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={}&MevzuatTur=1&MevzuatTertip=5"
    db = None

    KANUNLAR = [
        {"id": "5237", "isim": "Türk Ceza Kanunu",         "kisaAd": "TCK",  "kategori": "Ceza Hukuku",     "aciklama": "Suç ve ceza kavramlarını düzenleyen temel kanun."},
        {"id": "5271", "isim": "Ceza Muhakemesi Kanunu",   "kisaAd": "CMK",  "kategori": "Ceza Hukuku",     "aciklama": "Ceza yargılaması usullerini düzenler."},
        {"id": "4721", "isim": "Türk Medeni Kanunu",       "kisaAd": "TMK",  "kategori": "Özel Hukuk",      "aciklama": "Kişiler, aile, miras ve eşya hukukunu kapsar."},
        {"id": "6098", "isim": "Türk Borçlar Kanunu",      "kisaAd": "TBK",  "kategori": "Özel Hukuk",      "aciklama": "Borç ilişkilerini ve sözleşmeleri kapsar."},
        {"id": "6102", "isim": "Türk Ticaret Kanunu",      "kisaAd": "TTK",  "kategori": "Ticaret Hukuku",  "aciklama": "Ticari işletme, şirketler ve kıymetli evrak hukuku."},
        {"id": "4857", "isim": "İş Kanunu",                "kisaAd": "İK",   "kategori": "İş Hukuku",       "aciklama": "İşçi ve işveren ilişkilerini düzenler."},
        {"id": "2004", "isim": "İcra ve İflas Kanunu",     "kisaAd": "İİK",  "kategori": "Usul Hukuku",     "aciklama": "Cebri icra ve iflas usulünü düzenler."},
        {"id": "6362", "isim": "Sermaye Piyasası Kanunu",  "kisaAd": "SPK",  "kategori": "Ticaret Hukuku",  "aciklama": "Sermaye piyasası araçlarını ve kurumlarını düzenler."},
        {"id": "2709", "isim": "Türkiye Cumhuriyeti Anayasası", "kisaAd": "AY",   "kategori": "Kamu Hukuku",  "aciklama": "Devletin temel yapısını ve temel hakları düzenler."},
        {"id": "2577", "isim": "İdari Yargılama Usulü Kanunu",  "kisaAd": "İYUK", "kategori": "İdare Hukuku", "aciklama": "İdare mahkemelerindeki yargılama usulünü düzenler."},
        {"id": "5510", "isim": "Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu", "kisaAd": "SGSK", "kategori": "Sosyal Güvenlik", "aciklama": "Sosyal güvenlik sistemini düzenler."},
        {"id": "6458", "isim": "Yabancılar ve Uluslararası Koruma Kanunu", "kisaAd": "YUKK", "kategori": "İdare Hukuku", "aciklama": "Yabancıların Türkiye'deki statüsünü düzenler."},
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
    def _madde_id_formatla(cls, madde_no: str) -> str:
        s = str(madde_no).strip()
        if any(k in s.lower() for k in ["geçici", "ek"]):
            return s.title()
        return s.upper()

    # ------------------------------------------------------------------
    # 📄 ANA MADDE GETİRME — HİBRİT
    # ------------------------------------------------------------------
    @classmethod
    def madde_getir_buluttan(cls, kanun_kisa_adi: str, madde_no: str) -> dict:
        """
        1. Bedesten API → 2. Firebase cache → 3. Hata
        """
        # --- 1. BEDESTEN API ---
        sonuc = BedestenAPI.madde_ara(kanun_kisa_adi, madde_no)
        if sonuc:
            # Arka planda cache güncelle
            cls._firebase_yaz_sessiz(kanun_kisa_adi, sonuc)
            return sonuc

        # --- 2. FİREBASE CACHE ---
        try:
            cls.veritabanini_baslat()
            madde_id = cls._madde_id_formatla(madde_no)
            doc_ref = (cls.db
                       .collection("kanunlar")
                       .document(kanun_kisa_adi)
                       .collection("maddeler")
                       .document(madde_id))
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            pass

        raise ValueError(
            f"'{kanun_kisa_adi}' için Madde {madde_no} bulunamadı. "
            "Bedesten API ve yerel veritabanı kontrol edildi. "
            "Geliştirici panelinden 'Kanunu Yükle' işlemi deneyin."
        )

    @classmethod
    def _firebase_yaz_sessiz(cls, kanun_kisa_adi: str, madde: dict):
        try:
            cls.veritabanini_baslat()
            madde_id = cls._madde_id_formatla(madde.get("no", "X"))
            (cls.db
             .collection("kanunlar")
             .document(kanun_kisa_adi)
             .collection("maddeler")
             .document(madde_id)
             .set(madde, merge=True))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 🔍 KELİME ARAMASI
    # ------------------------------------------------------------------
    @classmethod
    def kelime_ile_ara(cls, kanun_kisa_adi: str, arama_terimi: str) -> list:
        """Firebase üzerinden tam metin arama (Bedesten bu özelliği tam desteklemiyor)."""
        try:
            cls.veritabanini_baslat()
            aranan = arama_terimi.lower()
            docs = (cls.db
                    .collection("kanunlar")
                    .document(kanun_kisa_adi)
                    .collection("maddeler")
                    .stream())
            sonuclar = []
            for doc in docs:
                veri = doc.to_dict()
                metin  = veri.get("metin", "").lower()
                baslik = veri.get("baslik", "").lower()
                if aranan in metin or aranan in baslik:
                    sonuclar.append(veri)
            return sorted(
                sonuclar,
                key=lambda x: int(x["no"]) if str(x["no"]).isdigit() else str(x["no"])
            )
        except Exception:
            return []

    # ------------------------------------------------------------------
    # 🤖 AI ANALİZ
    # ------------------------------------------------------------------
    @classmethod
    def madde_analiz_et(cls, api_key: str, madde_metni: str,
                        kanun_adi: str, madde_no: str, soru: str = "") -> str:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            prompt = f"""
            Sen profesyonel bir hukuk asistanısın. Aşağıda metni verilen kanun maddesini
            bir hukukçu titizliğiyle analiz et.
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

    # ------------------------------------------------------------------
    # 🔄 GELİŞTİRİCİ PANELİ — TOPLU YÜKLEME
    # ------------------------------------------------------------------
    @classmethod
    def kanunu_buluta_yukle(cls, kanun_id: str, kanun_kisa_adi: str, ozel_db=None):
        """
        Önce Bedesten API'sinden tüm maddeleri çekmeyi dener.
        Başarısız olursa mevzuat.gov.tr scraping'ine düşer.
        """
        current_db = ozel_db or cls.db
        if not current_db:
            cls.veritabanini_baslat()
            current_db = cls.db

        current_db.collection("kanunlar").document(kanun_kisa_adi).set(
            {"isim": kanun_kisa_adi, "durum": "Aktif"}, merge=True
        )
        kanun_ref = (current_db
                     .collection("kanunlar")
                     .document(kanun_kisa_adi)
                     .collection("maddeler"))

        # 1. BEDESTEN DENEMESİ
        st.info(f"🌐 [{kanun_kisa_adi}] Bedesten API deneniyor (Adalet Bakanlığı resmi sistemi)...")
        maddeler = BedestenAPI.kanun_tam_liste(kanun_kisa_adi)

        if maddeler:
            eklenen = 0
            for m in maddeler:
                m_no_ham = str(m.get("maddeNo", m.get("madde_numarasi", ""))).strip()
                m_no = m_no_ham.upper().replace("MADDE", "").strip()
                metin = m.get("metin", m.get("text", ""))
                baslik = m.get("baslik", m.get("madde_numarasi", f"Madde {m_no}"))
                if m_no and metin:
                    kanun_ref.document(m_no).set({
                        "no": m_no, "baslik": baslik, "metin": metin
                    })
                    eklenen += 1

            if eklenen > 0:
                st.success(f"✅ Bedesten API: {kanun_kisa_adi} → {eklenen} madde Firebase'e yazıldı!")
                st.balloons()
                return
            else:
                st.warning("Bedesten boş liste döndürdü, scraping'e geçiliyor...")

        # 2. SCRAPING FALLBACK
        st.warning(f"⚠️ [{kanun_kisa_adi}] mevzuat.gov.tr kazımasına geçiliyor...")
        cls._scraping_yukle(kanun_id, kanun_kisa_adi, kanun_ref)

    @classmethod
    def _scraping_yukle(cls, kanun_id: str, kanun_kisa_adi: str, kanun_ref):
        """Eski yöntem: mevzuat.gov.tr'den HTML kazıma."""
        url = cls.BASE_URL.format(kanun_id)
        try:
            html = ""
            for deneme in range(3):
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Connection": "keep-alive"
                    }
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=45) as response:
                        html = response.read().decode("utf-8")
                    break
                except Exception as e:
                    if deneme < 2:
                        st.warning(f"⏳ Site yavaş yanıt veriyor, {deneme + 2}. deneme yapılıyor...")
                        time.sleep(3)
                    else:
                        raise Exception(f"Mevzuat sitesi yanıt vermiyor: {str(e)}")

            soup = BeautifulSoup(html, "html.parser")
            metin_alani = soup.find(id="MevzuatMetin") or soup.find(id="MevzuatMetinBul") or soup

            for tag in metin_alani(["script", "style", "nav", "header", "footer", "button"]):
                tag.extract()
            for br in metin_alani.find_all("br"):
                br.replace_with("\n")
            for tag in metin_alani.find_all(["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
                tag.insert_before("\n")
                tag.insert_after("\n")

            saf_metin = metin_alani.get_text(separator="\n", strip=True)
            saf_metin = saf_metin.replace("\xa0", " ").replace("\r", "")
            saf_metin = re.sub(
                r"(?i)(?<!\n)((?:ek\s+|geçici\s+)?madde\s+[0-9]+[a-zçğıöşüA-Z/]*\s*[-\u2013\u2014])",
                r"\n\1", saf_metin
            )

            satirlar = saf_metin.split("\n")
            aktif_madde_no = None
            aktif_madde_metni = []
            aktif_madde_baslik = ""
            eklenen = 0

            for satir in satirlar:
                satir = satir.strip()
                if not satir:
                    continue
                match = re.search(
                    r"^\W*(ek\s+|geçici\s+)?madde\s*([0-9]+[a-zçğıöşüA-Z/]*)",
                    satir, re.IGNORECASE
                )
                if match:
                    if aktif_madde_no:
                        kanun_ref.document(str(aktif_madde_no)).set({
                            "no": aktif_madde_no,
                            "baslik": aktif_madde_baslik,
                            "metin": "\n\n".join(aktif_madde_metni)
                        })
                        eklenen += 1
                    on_ek = match.group(1).strip().capitalize() + " " if match.group(1) else ""
                    asil_no = match.group(2).upper()
                    aktif_madde_no = f"{on_ek}{asil_no}".strip()
                    parcalar = re.split(r"[-\u2013\u2014]", satir, maxsplit=1)
                    aktif_madde_baslik = parcalar[1].strip() if len(parcalar) > 1 else f"{on_ek}Madde {asil_no}".strip()
                    aktif_madde_metni = []
                elif aktif_madde_no:
                    aktif_madde_metni.append(satir)

            if aktif_madde_no:
                kanun_ref.document(str(aktif_madde_no)).set({
                    "no": aktif_madde_no,
                    "baslik": aktif_madde_baslik,
                    "metin": "\n\n".join(aktif_madde_metni)
                })
                eklenen += 1

            if eklenen > 0:
                st.success(f"✅ Scraping ile {kanun_kisa_adi} → {eklenen} madde Firebase'e yazıldı!")
                st.balloons()
            else:
                st.error(f"⚠️ {kanun_kisa_adi} için 0 madde bulundu! Site içeriği okunamadı.")

        except Exception as e:
            st.error(f"❌ Hata ({kanun_kisa_adi}): {str(e)}")
