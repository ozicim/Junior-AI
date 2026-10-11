import google.generativeai as genai
import firebase_admin
import PyPDF2
import io
import json
import requests
import streamlit as st
import os
import zipfile
import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
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
                    firebase_info["private_key"] = firebase_info["private_key"].replace(
                        "\\n", "\n"
                    )
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
            cls._hoca_model = genai.GenerativeModel("models/gemini-2.5-flash")

        return cls._hoca_model

    @classmethod
    def get_akademik_mufredat(cls):
        """Dersleri sınıflara göre gruplandıran ana kütüphane."""
        return {
            "1. Sınıf": [
                {"id": "hukuk_baslangici", "isim": "Hukuk Başlangıcı", "ikon": "📜"},
                {"id": "anayasa", "isim": "Anayasa Hukuku", "ikon": "🏛️"},
                {"id": "roma", "isim": "Roma Hukuku", "ikon": "⚖️"},
                {"id": "iktisat", "isim": "İktisat", "ikon": "📈"},
                {"id": "medeni", "isim": "Medeni Hukuk", "ikon": "🏠"},
            ],
            "2. Sınıf": [
                {"id": "ceza_genel", "isim": "Ceza Hukuku (Genel)", "ikon": "⛓️"},
                {"id": "borclar_genel", "isim": "Borçlar Hukuku (Genel)", "ikon": "🤝"},
                {"id": "idare", "isim": "İdare Hukuku", "ikon": "🏢"},
                {
                    "id": "hukuk_felsefesi",
                    "isim": "Hukuk Felsefesi ve Sosyolojisi",
                    "ikon": "🧠",
                },
                {
                    "id": "milletlerarasi_kamu",
                    "isim": "Milletlerarası Hukuk",
                    "ikon": "🌍",
                },
                {"id": "hukuk_tarihi", "isim": "Türk Hukuk Tarihi", "ikon": "📚"},
            ],
            "3. Sınıf": [
                {"id": "ceza_ozel", "isim": "Ceza Hukuku (Özel)", "ikon": "🔍"},
                {"id": "borclar_ozel", "isim": "Borçlar Hukuku (Özel)", "ikon": "📑"},
                {"id": "ticaret", "isim": "Ticaret Hukuku", "ikon": "💼"},
                {"id": "medeni_usul", "isim": "Medeni Usul Hukuku", "ikon": "👨‍⚖️"},
                {
                    "id": "idari_yargilama",
                    "isim": "İdari Yargılama Hukuku",
                    "ikon": "⚔️",
                },
                {"id": "esya", "isim": "Eşya Hukuku", "ikon": "🏡"},
            ],
            "4. Sınıf": [
                {
                    "id": "milletlerarasi_ozel",
                    "isim": "Milletlerarası Özel Hukuk",
                    "ikon": "🌐",
                },
                {"id": "is", "isim": "İş Hukuku", "ikon": "👷"},
                {"id": "icra_iflas", "isim": "İcra ve İflas Hukuku", "ikon": "🔨"},
                {
                    "id": "ceza_muhakemeleri",
                    "isim": "Ceza Muhakemeleri Hukuku",
                    "ikon": "⚖️",
                },
                {"id": "kiymetli_evrak", "isim": "Kıymetli Evrak Hukuku", "ikon": "💳"},
                {"id": "miras", "isim": "Miras Hukuku", "ikon": "👪"},
                {"id": "genel_kamu", "isim": "Genel Kamu Hukuku", "ikon": "🏛️"},
                {
                    "id": "sosyal_guvenlik",
                    "isim": "Sosyal Güvenlik Hukuku",
                    "ikon": "🛡️",
                },
            ],
        }

    @classmethod
    def get_ders_notu_icerik(cls, ders_id, konu_id):
        veriler = {
            "hukuk_giris": {
                "normlar_hiyerarsisi": "Normlar hiyerarşisi, hukuk kurallarının derece ve kuvvetini belirleyen alt-üst ilişkisidir...",
                "hak_ehliyeti": "Hak ehliyeti, her insanın sağ ve tam doğmak şartıyla kazandığı bir yetenektir...",
            }
        }
        return veriler.get(ders_id, {}).get(
            konu_id, "Bu konu hakkında henüz bir not eklenmemiş."
        )

    @classmethod
    def yuklenen_notlari_getir(cls):
        try:
            cls.veritabanini_baslat()
            docs = cls.db.collection("ders_notlari").stream()
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
        try:
            cls.veritabanini_baslat()
            docs = (
                cls.db.collection("ders_notlari")
                .where("dosya_adi", "==", dosya_adi)
                .stream()
            )
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
        try:
            cls.veritabanini_baslat()
            docs = (
                cls.db.collection("ders_notlari")
                .where("dosya_adi", "==", dosya_adi)
                .stream()
            )
            for doc in docs:
                veri = doc.to_dict()
                return veri.get("metin", "")
            return ""
        except Exception as e:
            print(f"Metin çekme hatası: {e}")
            return ""

    @classmethod
    def dosyadan_metin_cikar(cls, yuklenen_dosya):
        if yuklenen_dosya.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(yuklenen_dosya)
            metin = ""
            for sayfa in pdf_reader.pages:
                t = sayfa.extract_text()
                if t:
                    metin += t + "\n"
            return metin
        else:
            return str(yuklenen_dosya.read(), "utf-8")

    @classmethod
    def notlarla_ai_hoca_anlat(cls, api_key, konu_adi, ders_notu_metni):
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
            - Konuyu öğrencinin anlayacağı şekilde, notlardaki bilgileri derinleştirerek anlat.

            FORMAT (Sadece bu başlıkları kullan):
            ### 🏛️ {konu_adi.upper()} - KÜRSÜ NOTLARI (ARŞİV ANALİZİ)
            **1. Konunun Teorik Temeli:** Bu kurumun hukuk sistemindeki yeri ve mantığı nedir?
            **2. Doktrindeki Tartışmalar:** Notlarda geçen veya bu konudaki akademik ayrışmalar nelerdir?
            **3. Kanunun Ruhu ve Analiz:** Maddenin lafzı ne der, ruhu neyi amaçlar?
            **💡 Hocanın Notu (Sınav Tüyosu):** Bu notlardan sınavda ne gelir? Nereye dikkat edilmeli?
            **📚 İleri Okuma Önerisi:** Bu notu tamamlamak için hangi kavramlara bakılmalı?
            """

            response = model.generate_content(prompt)
            return (
                response.text
                if response and response.text
                else "⚠️ Hoca notları incelerken bir sorunla karşılaştı."
            )
        except Exception as e:
            return f"Hoca notları okuyamadı: {str(e)}"

    @classmethod
    def zip_arsivinden_not_bul(cls, ders_adi):
        zip_dosya_adi = "akademi_notlari.zip"
        ic_dosya_adi = "akademi_notlari.json"

        if not os.path.exists(zip_dosya_adi):
            return "⚠️ Junilex Akademi Arşivi bulunamadı!"

        try:
            with zipfile.ZipFile(zip_dosya_adi, "r") as z:
                with z.open(ic_dosya_adi) as f:
                    tum_notlar = json.loads(f.read().decode("utf-8"))

            aranan_saf = ders_adi.lower()
            aranan_temiz = re.sub(r"[^\w\s]", "", aranan_saf).strip()
            anahtar = aranan_temiz.split("hukuku")[0].strip()

            bulunan_notlar = []
            for not_item in tum_notlar:
                db_ders = not_item.get("ders_adi", "").lower()
                db_konu = not_item.get("konu_basligi", "").lower()

                db_ders_temiz = re.sub(r"[^\w\s]", "", db_ders).strip()
                db_konu_temiz = re.sub(r"[^\w\s]", "", db_konu).strip()

                if anahtar not in db_ders_temiz:
                    continue

                if "genel" in aranan_saf and not (
                    "genel" in db_ders_temiz or "genel" in db_konu_temiz
                ):
                    continue
                if "özel" in aranan_saf or "ozel" in aranan_saf:
                    if not (
                        "özel" in db_ders_temiz
                        or "ozel" in db_ders_temiz
                        or "özel" in db_konu_temiz
                        or "ozel" in db_konu_temiz
                    ):
                        continue
                if ("muhakeme" in aranan_saf) != (
                    "muhakeme" in db_ders_temiz or "muhakeme" in db_konu_temiz
                ):
                    continue
                if ("usul" in aranan_saf) != (
                    "usul" in db_ders_temiz or "usul" in db_konu_temiz
                ):
                    continue

                bulunan_notlar.append(not_item.get("ders_notu", ""))

            if bulunan_notlar:
                birlesik_not = "\n\n--- BAŞKA BİR NOT ---\n\n".join(bulunan_notlar)
                return birlesik_not[:25000]

            return "⚠️ Bu derse ait arşivlenmiş ders notu bulunamadı."
        except Exception as e:
            return f"⚠️ Arşiv okuma hatası: {str(e)}"

    @classmethod
    def mufredat_hoca_anlat(cls, gemini_key, serper_key, ders, soru):
        try:
            if not os.path.exists("faiss_index") and os.path.exists("faiss_index.zip"):
                with zipfile.ZipFile("faiss_index.zip", "r") as zip_ref:
                    zip_ref.extractall("faiss_index")

            if not os.path.exists("faiss_index"):

                def hata_generator():
                    yield "⚠️ Vektör veritabanı (faiss_index.zip) bulunamadı!"

                return hata_generator()

            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vector_store = FAISS.load_local(
                "faiss_index", embeddings, allow_dangerous_deserialization=True
            )

            arama_metni = f"Ders: {ders}. Soru: {soru}"
            en_iyi_eslesmeler = vector_store.similarity_search(arama_metni, k=5)

            context = "\n\n--- İLGİLİ ARŞİV BÖLÜMÜ ---\n\n".join(
                [doc.page_content for doc in en_iyi_eslesmeler]
            )

            model = cls._modeli_hazirla(gemini_key)
            prompt = f"""
            SEN KIDEMLİ BİR HUKUK PROFESÖRÜSÜN.
            Ders: {ders}
            
            ÖĞRENCİNİN SORUSU:
            {soru}
            
            ELİNDEKİ JUNILEX AKILLI FİHRİST NOTLARI:
            {context}
            
            GÖREVİN:
            İnternetten veya kendi hafızandan bilgi uydurma. Sadece yukarıdaki "Fihrist Notları"nı kullanarak öğrencinin sorusunu akademik bir dille yanıtla. Eğer notlarda soruyla ilgili hiçbir bilgi yoksa, "Bu spesifik konu mevcut arşivimde yer almıyor" diyerek dürüst ol.
            """

            response = model.generate_content(prompt, stream=True)
            return (chunk.text for chunk in response if chunk.text)

        except Exception as e:
            hata_mesaji = str(e)

            def hata_generator():
                yield f"⚠️ Profesör veritabanına bağlanamadı (Teknik Hata): {hata_mesaji}"

            return hata_generator()

    @classmethod
    def kavram_haritasi_uret(cls, api_key: str, ders_adi: str, konu_adi: str):
        """
        Seçilen hukuki konu için hiyerarşik zihin haritası (Mind Map) ve sınav kavram şeması üretir.
        """
        try:
            model = cls._modeli_hazirla(api_key)

            prompt = f"""
            SEN KIDEMLİ BİR HUKUK PROFESÖRÜ VE ZİHİN HARİTASI (MIND MAP) UZMANISIN.
            Ders: {ders_adi}
            Konu: {konu_adi}

            GÖREVİN:
            Öğrencinin vize ve final sınavlarına hazırlanırken tek bakışta konunun mantığını anlayabileceği görsel ve hiyerarşik bir HUKUKİ KAVRAM HARİTASI (ZİHİN HARİTASI) oluşturmak.

            ANLATIM VE FORMAT KURALLARI:
            - Net, anlaşılır, girintili (bullet points) ve hiyerarşik bir ağaç yapısı kullan.
            - Sadece aşağıdaki ana başlıkları kullan:

            ### 📊 VİZE & FİNAL HUKUKİ KAVRAM HARİTASI: {konu_adi.upper()}

            **1. 📌 Kurumun Tanımı ve Hukuki Niteliği**
            - Temel Tanım: ...
            - Hukuki Niteliği: ...
            - İlgili Kanun Maddesi/Maddeleri: ...

            **2. ⚙️ Kurumun Unsurları ve Şartları (Zorunlu Ögeler)**
            - 🔹 Unsurlar:
              - ...
              - ...
            - 🔹 Geçerlilik Şartları:
              - ...

            **3. ⚡ Hüküm ve Sonuçları / İstisnalar**
            - 🎯 Hukuki Sonuçlar:
              - ...
            - ⚠️ Kritik İstisnalar / Özel Durumlar:
              - ...

            **4. 🔍 Sınavlarda Çeldirici Olarak Gelen Karıştırılan Kavramlar**
            - ❌ X Kavramı ile Farkı: ...
            - ❌ Y Kavramı ile Farkı: ...

            **5. 💡 Sınav Zihin Kodu (Tek Cümlelik Hatırlatıcı)**
            - ...
            """

            response = model.generate_content(prompt, stream=True)
            return (chunk.text for chunk in response if chunk.text)

        except Exception as e:
            hata_mesaji = str(e)

            def hata_generator():
                yield f"⚠️ Kavram haritası üretilirken teknik bir hata oluştu: {hata_mesaji}"

            return hata_generator()

    @classmethod
    def podcast_senaryosu_uret(cls, api_key: str, ham_metin: str) -> str:
        """
        Ham akademik metni, sohbet havasında, NotebookLM tarzı bir podcast senaryosuna dönüştürür.
        """
        try:
            model = cls._modeli_hazirla(api_key)
            prompt = f"""
            Aşağıda hukuk fakültesi öğrencileri için üretilmiş bir akademik metin (veya zihin haritası) bulunuyor. 
            Senden bu metni dümdüz okumak yerine; Google NotebookLM'in sesli özetlerine benzer şekilde, **sohbet havasında, ilgi çekici, akıcı ve öğretici bir podcast (sesli yayın) metnine** dönüştürmeni istiyorum.
            
            KURALLAR:
            1. Metni bir radyo sunucusu veya cana yakın, tecrübeli bir hukuk profesörü gibi anlat. Girişte dinleyicileri selamla ("Merhaba geleceğin hukukçuları, Junilex Podcast'e hoş geldiniz..." gibi).
            2. Karşında bir hukuk öğrencisi varmış gibi konuş. Karmaşık maddeleri ve unsurları basitleştirerek, sanki bir hikaye anlatıyormuş gibi günlük dilden bağlar kurarak anlat.
            3. "1. Madde, 2. Madde" diye robotik listelemeler yapmak yerine "Şimdi gelelim en önemli noktaya...", "Burada dikkat etmeniz gereken çok kritik bir istisna var, sınavda hayat kurtarır..." gibi bağlaçlar kullan.
            4. Metin doğrudan Text-to-Speech (TTS) motoru ile sese çevrileceği için HİÇBİR ŞEKİLDE parantez içi eylem/efekt (gülümser, duraklar, nefes alır, müzik girer) KULLANMA. Sadece ağızdan çıkacak kelimeleri yaz.
            5. Ücretsiz ses motorunda tek bir ses olduğu için karşılıklı diyalog yazma, **tek bir sunucu/hoca** baştan sona anlatacak şekilde kurgula.
            6. Uzunluğu çok abartma, ortalama 2-3 dakikalık bir okuma süresine denk gelecek akıcılıkta tut.
            
            İŞTE DÖNÜŞTÜRÜLECEK HAM METİN:
            {ham_metin}
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Podcast senaryosu üretilirken hata: {e}")
            return ham_metin  # Hata olursa fail-safe olarak orijinal metni döndür

    @classmethod
    def flashcard_uret(cls, api_key: str, ders_adi: str, konu_adi: str):
        """
        Seçilen hukuki konudan Anki tarzı flashcard (ezber kartı) verilerini JSON formatında üretir.
        """
        try:
            import json
            import re

            model = cls._modeli_hazirla(api_key)
            prompt = f"""
            SEN BİR HUKUK PROFESÖRÜSÜN. Hukuk fakültesi öğrencilerinin vizelere hazırlanırken kavramları ezberlemesi için Anki tarzı flaş kartlar (flashcards) hazırlayacaksın.
            Ders: {ders_adi}
            Konu: {konu_adi}

            GÖREVİN:
            Bu konudaki en önemli kavramları, unsurları, süreleri ve istisnaları içeren tam 10 adet flaş kart üretmek.
            
            KURAL: 
            Sadece ve sadece aşağıdaki JSON formatında çıktı ver. Markdown işaretleri (```json vb.) kullanabilirsin ama dışında hiçbir açıklama veya metin yazma.

            [
                {{
                    "on_yuz": "Kavram, terim veya kilit soru (Örn: Haksız Fiilin Unsurları Nelerdir?)",
                    "arka_yuz": "Kısa, net ve ezberlenebilir cevap/tanım (Örn: 1. Hukuka aykırı fiil, 2. Kusur, 3. Zarar, 4. İlliyet bağı)"
                }},
                {{
                    "on_yuz": "Kavram 2",
                    "arka_yuz": "Cevap 2"
                }}
            ]
            """

            response = model.generate_content(prompt)
            metin = response.text

            # AI bazen metnin başına sonuna ```json koyabilir, onu temizleyip parse edelim:
            json_match = re.search(r"\[.*\]", metin, re.DOTALL)
            if json_match:
                kart_verisi = json.loads(json_match.group())
                return kart_verisi
            else:
                return {"hata": "Yapay zeka geçerli bir JSON formatı üretemedi."}

        except Exception as e:
            return {"hata": str(e)}
