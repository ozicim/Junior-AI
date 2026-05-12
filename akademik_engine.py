import google.generativeai as genai
import firebase_admin
import PyPDF2
import io
import streamlit as st
from firebase_admin import credentials, firestore

class AkademikEngine:
    db = None

    @classmethod # <-- Bu eksikti, eklendi
    def veritabanini_baslat(cls):
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase-anahtar.json")
            firebase_admin.initialize_app(cred)
        if not cls.db:
            cls.db = firestore.client()

    @classmethod
    def get_akademik_mufredat(cls):
        return {
            "1. Sınıf": [
                {"id": "hukuk_baslangici", "isim": "Hukuk Başlangıcı", "ikon": "📜"},
                {"id": "anayasa_genel", "isim": "Anayasa Hukuku (Genel)", "ikon": "⚖️"},
                {"id": "roma_hukuku", "isim": "Roma Hukuku", "ikon": "🏛️"},
                {"id" : "iktisat", "isim": "İktisat", "ikon": "📈"},
                {"id" : "medeni", "isim": "Medeni Hukuk (Genel)", "ikon": "🏠"},
            ],
            "2. Sınıf": [
                {"id": "ceza_genel", "isim": "Ceza Hukuku (Genel)", "ikon": "⛓️"},
                {"id": "idare_hukuku", "isim": "İdare Hukuku", "ikon": "🏢"},
                {"id": "borclar_genel", "isim": "Borçlar Hukuku (Genel)", "ikon": "🤝"},
                {"id" : "hukuk_felsefesi", "isim": "Hukuk Felsefesi ve Sosyolojisi", "ikon": "🧠"},
                {"id" : "milletlerarasi_hukuk", "isim": "Milletlerarası Hukuk", "ikon": "🌍"},
                {"id" : "hukuk_tarihi", "isim": "Türk Hukuk Tarihi", "ikon": "📚"},
            ],
            "3. Sınıf": [
                {"id": "ceza_ozel", "isim": "Ceza Hukuku (Özel)", "ikon": "🔍"},
                {"id": "medeni_usul", "isim": "Medeni Usul Hukuku", "ikon": "👨‍⚖️"},
                {"id": "ticaret_hukuku", "isim": "Ticaret Hukuku", "ikon": "💼"},
                {"id" : "borclar_ozel", "isim": "Borçlar Hukuku (Özel)", "ikon": "📑"},
                {"id" : "idari_yargi", "isim": "İdari Yargı Hukuku", "ikon": "⚔️"},
                {"id" : "esya", "isim": "Eşya Hukuku", "ikon": "🏡"},
            ],
            "4. Sınıf": [
                {"id": "icra_iflas", "isim": "İcra İflas Hukuku", "ikon": "🔨"},
                {"id": "ozel_milletlerarasi", "isim": "Milletlerarası Özel Hukuk", "ikon": "🌐"},
                {"id": "is_hukuku", "isim": "İş Hukuku", "ikon": "👷"},
                {"id" : "kiymetli_evrak", "isim": "Kıymetli Evrak Hukuku", "ikon": "💳"},
                {"id" : "ceza_muhakemesi", "isim": "Ceza Muhakemesi Hukuku", "ikon": "⚖️"},
                {"id" : "miras", "isim": "Miras Hukuku", "ikon": "👪"},
                {"id": "genel_kamu_hukuku", "isim": "Genel Kamu Hukuku", "ikon": "🏛️"},
                {"id" : "sosyal_guvenlik", "isim": "Sosyal Güvenlik Hukuku", "ikon": "🛡️"},
            ]
        }

    @classmethod
    def yuklenen_notlari_getir(cls):
        """Firestore'dan tüm ders notlarının isimlerini çeker.""" # <-- Girinti düzeltildi
        try:
            from firebase_admin import firestore
            db = firestore.client()
            docs = db.collection("ders_notlari").stream()
            not_listesi = []
            for doc in docs:
                veri = doc.to_dict()
                if "dosya_adi" in veri:
                    not_listesi.append(veri["dosya_adi"])
            return list(set(not_listesi)) # <-- Girinti düzeltildi
        except Exception as e:
            return []

    @classmethod
    def dosyadan_metin_cikar(cls, yuklenen_dosya):
        if yuklenen_dosya.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(yuklenen_dosya)
            metin = ""
            for sayfa in pdf_reader.pages:
                metin += sayfa.extract_text()
            return metin
        else:
            return str(yuklenen_dosya.read(), "utf-8")

    @classmethod
    def notlarla_ai_hoca_anlat(cls, api_key, konu_adi, ders_notu_metni):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash') # İsmi düzelttik
            prompt = f"Sen profesyonel bir hukuk hocasısın... {ders_notu_metni[:10000]}"
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Hata: {str(e)}"
