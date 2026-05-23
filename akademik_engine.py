import google.generativeai as genai
import firebase_admin
import PyPDF2
import io
import json
import requests
import streamlit as st
import os
import zipfile
from firebase_admin import credentials, firestore

class AkademikEngine:
    db = None
    _hoca_model = None
    _configured_key = None
    
    @classmethod
    def veritabanini_baslat(cls):
        if not firebase_admin._apps:
            try:
                firebase_info = dict(st.secrets["firebase"])
                
                if "private_key" in firebase_info:
                    firebase_info["private_key"] = firebase_info["private_key"].replace("\\n", "\n")
                
                cred = credentials.Certificate(firebase_info)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                st.error(f"Secrets üzerinden Firebase başlatılamadı: {e}")
                
        if cls.db is None:
            cls.db = firestore.client()

    @classmethod
    def _modeli_hazirla(cls, api_key):
        """Modeli cache'le — her analizde yeniden oluşturma"""
        if cls._configured_key != api_key:
            genai.configure(api_key=api_key)
            cls._configured_key = api_key
            cls._hoca_model = None

        if cls._hoca_model is None:
            cls._hoca_model = genai.GenerativeModel('models/gemini-2.5-flash')

        return cls._hoca_model

    @classmethod
    def get_akademik_mufredat(cls):
        """Dersleri sınıflara göre gruplandıran ana kütüphane."""
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
                return veri.get("metin", "")
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
        """Yüklenen ders notlarını baz alarak bir Profesör gibi konu anlatımı yapar."""
        try:
            model = cls._modeli_hazirla(api_key)

            prompt = f"""
            SEN KIDEMLİ BİR HUKUK PROFESÖRÜSÜN. Kürsüdesin ve karşında hukuk öğrencileri var.
            Konu: {konu_adi}
            
            ELİNDEKİ DERS NOTU İÇERİĞİ:
            {ders_notu_metni}
            
            GÖREVİN:
            Bu konuyu, yukarıdaki ders notlarını temel alarak bir AKADEMİSYEN gibi anlat. 
            Yargıtay kararlarından ziyade kanunun ruhuna, doktrindeki tartışmalara ve teorik temellere odaklan.

            ANLATIM TARZI:
            - "Hukuki niteliği şudur...", "Doktrinde baskın görüş...", "Kanun koyucunun amacı..." gibi akademik kalıplar kullan.
            - Konuyu öğrencinin (Ozan Şahin Sicim) anlayacağı şekilde, notlardaki bilgileri derinleştirerek anlat.

            FORMAT (Sadece bu başlıkları kullan):
            ### 🏛️ {konu_adi.upper()} - KÜRSÜ NOTLARI (ARŞİV ANALİZİ)
            **1. Konunun Teorik Temeli:** Bu kurumun hukuk sistemindeki yeri ve mantığı nedir?
            **2. Doktrindeki Tartışmalar:** Notlarda geçen veya bu konudaki akademik ayrışmalar nelerdir?
            **3. Kanunun Ruhu ve Analiz:** Maddenin lafzı ne der, ruhu neyi amaçlar?
            **💡 Hocanın Notu (Sınav Tüyosu):** Bu notlardan sınavda ne gelir? Nereye dikkat edilmeli?
            **📚 İleri Okuma Önerisi:** Bu notu tamamlamak için hangi kavramlara bakılmalı?
            """
            
            response = model.generate_content(prompt)
            
            if response and hasattr(response, 'candidates') and len(response.candidates) > 0:
                try:
                    return response.text
                except (ValueError, AttributeError):
                    return "⚠️ Hoca notları incelerken bir sorunla karşılaştı, metin oluşturulamadı."
            else:
                return "⚠️ Model notlara ulaşamadı veya boş döndü."

        except Exception as e:
            return f"Hoca notları okuyamadı: {str(e)}"

    # ============================================================
    # [YENİ EKLENDİ] - ZIP'TEN MÜFREDAT NOTU BULMA MOTORU
    # ============================================================
    @classmethod
    def zip_arsivinden_not_bul(cls, ders_adi):
        """Seçilen derse ait notları arşivden çeker, usul ve muhakeme ayrımlarını kesin olarak korur."""
        import os
        import json
        import zipfile
        import re
        
        zip_dosya_adi = "akademi_notlari.zip"
        ic_dosya_adi = "akademi_notlari.json"
        
        if not os.path.exists(zip_dosya_adi):
            return "⚠️ Junilex Akademi Arşivi (akademi_notlari.zip) bulunamadı!"
            
        try:
            with zipfile.ZipFile(zip_dosya_adi, 'r') as z:
                with z.open(ic_dosya_adi) as f:
                    tum_notlar = json.loads(f.read().decode('utf-8'))
                    
            # Arayüzden gelen "Ceza Hukuku (Genel)" verisini "ceza hukuku"na çeviriyoruz
            aranan_temiz = re.sub(r'\(.*?\)', '', ders_adi).strip().lower()
            
            bulunan_notlar = []
            
            for not_item in tum_notlar:
                db_ders = not_item.get("ders_adi", "").lower()
                # Arşivdeki "⚖️ Ceza Hukuku" verisini "ceza hukuku"na çeviriyoruz
                db_ders_temiz = re.sub(r'[^\w\s]', '', db_ders).strip()
                
                # 1. KRİTİK FİLTRE: Muhakeme ve Usul ayrımlarını koru
                # Biri "muhakeme" içeriyorsa, eşleşmesi için diğerinin de içermesi ŞARTTIR.
                if ("muhakeme" in aranan_temiz) != ("muhakeme" in db_ders_temiz):
                    continue
                if ("usul" in aranan_temiz) != ("usul" in db_ders_temiz):
                    continue
                    
                # 2. EŞLEŞTİRME: Kalan temizlenmiş metinler birbirini kapsıyorsa notu al
                if aranan_temiz in db_ders_temiz or db_ders_temiz in aranan_temiz:
                    bulunan_notlar.append(not_item.get("ders_notu", ""))
                    
            if bulunan_notlar:
                birlesik_not = "\n\n--- BAŞKA BİR NOT ---\n\n".join(bulunan_notlar)
                return birlesik_not[:25000]
                
            return "⚠️ Bu derse ait arşivlenmiş ders notu bulunamadı."
        except Exception as e:
            return f"⚠️ Arşiv okuma hatası: {str(e)}"
    @classmethod
    def mufredat_hoca_anlat(cls, gemini_key, serper_key, ders, soru):
        """Ders notlarını baz alarak öğrencinin sorusunu yanıtlar."""
        try:
            arsiv_notu = cls.zip_arsivinden_not_bul(ders)
            model = cls._modeli_hazirla(gemini_key)

            prompt = f"""
            SEN KIDEMLİ BİR HUKUK PROFESÖRÜSÜN.
            Ders: {ders}
            
            ÖĞRENCİNİN SORUSU / TALEBİ:
            {soru}
            
            ELİNDEKİ JUNILEX DERS ARŞİVİ (Sadece bu bilgileri kullanarak yanıtla):
            {arsiv_notu}
            
            GÖREVİN:
            Öğrencinin sorusunu, İNTERNETTEN BİLGİ UYDURMADAN sadece elindeki 'Junilex Ders Arşivi'ni temel alarak bir AKADEMİSYEN gibi yanıtla. 
            Arşivde soruyla ilgili bilgi yoksa "Arşivimde bu konuya dair not bulunmuyor" diyerek dürüst ol.

            FORMAT:
            Öğrencinin sorusuna doğrudan ve akademik bir dille cevap ver. Gereksiz şablon başlıkları kullanma, doğrudan yanıtı yapılandır.
            """
            
            response = model.generate_content(prompt, stream=True)
            return (chunk.text for chunk in response if chunk.text)

        except Exception as e:
            def hata_generator():
                yield f"⚠️ Hoca odasında bulunamadı (Teknik Hata): {str(e)}"
            return hata_generator()
