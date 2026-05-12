import google.generativeai as genai
import firebase_admin
import PyPDF2
import io
import streamlit as st
from firebase_admin import credentials, firestore

class AkademikEngine:
    db = None
    
    @classmethod
    def veritabanini_baslat(cls):
        if not firebase_admin._apps:
            # DİKKAT: Artık dosya yolu değil, Secrets içindeki sözlüğü veriyoruz
            try:
                # Streamlit secrets içindeki bilgileri bir sözlük (dict) olarak alıyoruz
                firebase_info = dict(st.secrets["firebase_credentials"])
                
                # private_key içindeki \n karakterlerini düzeltmemiz gerekebilir
                if "private_key" in firebase_info:
                    firebase_info["private_key"] = firebase_info["private_key"].replace("\\n", "\n")
                
                cred = credentials.Certificate(firebase_info)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                st.error(f"Secrets üzerinden Firebase başlatılamadı: {e}")
                
        if not cls.db:
            cls.db = firestore.client()

    @classmethod
    def get_akademik_mufredat(cls):
        """
        Dersleri sınıflara göre gruplandıran ana kütüphane.
        Ustam, sen listeyi attığında burayı saniyeler içinde güncelleyeceğiz.
        """
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
    def get_ders_notu_icerik(cls, ders_id, konu_id):
        """Seçilen dersin ilgili konusuna ait notu getirir."""
        veriler = {
            "hukuk_giris": {
                "normlar_hiyerarsisi": "Normlar hiyerarşisi, hukuk kurallarının derece ve kuvvetini belirleyen alt-üst ilişkisidir...",
                "hak_ehliyeti": "Hak ehliyeti, her insanın sağ ve tam doğmak şartıyla kazandığı bir yetenektir..."
            }
        }
        return veriler.get(ders_id, {}).get(konu_id, "Bu konu hakkında henüz bir not eklenmemiş.")
        
    @classmethod
    def yuklenen_notlari_getir(cls):
        """Firestore'dan tüm ders notlarının isimlerini çeker."""
        try:
            from firebase_admin import firestore 
            db = firestore.client()
            docs = db.collection("ders_notlari").stream()
            not_listesi = []
            for doc in docs:
                veri = doc.to_dict()
                if "dosya_adi" in veri:
                    not_listesi.append(veri["dosya_adi"])
            return list(set(not_listesi))
        except Exception as e:
            print(f"Hata: {e}")
            return []
            
    @classmethod
    def not_sil(cls, dosya_adi):
        """Firestore'dan belirtilen isimdeki ders notunu siler."""
        try:
            from firebase_admin import firestore
            db = firestore.client()
            docs = db.collection("ders_notlari").where("dosya_adi", "==", dosya_adi).stream()
            silindi_mi = False
            for doc in docs:
                doc.reference.delete()
                silindi_mi = True
            return silindi_mi
        except Exception as e:
            print(f"Silme hatası: {e}")
            return False
            
    @classmethod
    def not_icerigi_getir(cls, dosya_adi):
        """Firestore'dan belirtilen dosyanın metin içeriğini getirir."""
        try:
            from firebase_admin import firestore
            db = firestore.client()
            docs = db.collection("ders_notlari").where("dosya_adi", "==", dosya_adi).stream()
            for doc in docs:
                veri = doc.to_dict()
                return veri.get("metin", "") # Metni geri döndür
            return ""
        except Exception as e:
            print(f"Metin çekme hatası: {e}")
            return ""

    @classmethod
    def dosyadan_metin_cikar(cls, yuklenen_dosya):
        """Yüklenen PDF veya TXT dosyasını metne çevirir."""
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
        """Yüklenen ders notlarını baz alarak konu anlatımı yapar."""
        try:
            genai.configure(api_key)
            model = genai.GenerativeModel('gemini-3-flash')
            
            prompt = f"""
            Sen profesyonel bir hukuk hocasısın. Aşağıda bir öğrencinin sana sağladığı 'Ders Notları' bulunmaktadır.
            
            ÖĞRENCİ NOTLARI:
            {ders_notu_metni[:40000]} # Bellek sınırı için ilk 10bin karakteri alıyoruz
            
            GÖREVİN:
            Öğrencinin sorduğu "{konu_adi}" konusunu, ÖNCELİKLE YUKARIDAKİ DERS NOTLARINA DAYANARAK anlat. 
            Eğer notlarda bilgi eksikse, genel hukuk bilginle tamamla ama notlardaki özel vurguları (hocanın görüşü, sınav tüyosu vb.) asla atlama.
            """
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Hoca notları okurken bir sorun yaşadı: {str(e)}"
