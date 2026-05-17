import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import chromadb
from sentence_transformers import SentenceTransformer

# RAG Motorunu Global Başlat (Her sorguda baştan yüklenmesin diye)
chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
collection = chroma_client.get_or_create_collection(name="turk_mevzuati")
embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

class ChatEngine:
    
    @staticmethod
    def kvkk_maskele(metin):
        """Metin içindeki TC ve Telefon numaralarını maskeler."""
        # 11 Haneli TC Kimlik Numarası Formatı
        metin = re.sub(r'\b[1-9][0-9]{10}\b', '[TC_KİMLİK_GİZLENDİ]', metin)
        # 05 ile başlayan telefon numarası formatı
        metin = re.sub(r'\b05\d{9}\b', '[TELEFON_GİZLENDİ]', metin)
        return metin

    @staticmethod
    def _rag_baglami_getir(soru, max_sonuc=3):
        """Kullanıcının sorusuna en uygun 3 kanun maddesini ChromaDB'den çeker."""
        try:
            soru_vektoru = embedding_model.encode(soru).tolist()
            sonuclar = collection.query(
                query_embeddings=[soru_vektoru],
                n_results=max_sonuc
            )
            
            baglam_metni = ""
            if sonuclar and sonuclar['documents'] and len(sonuclar['documents'][0]) > 0:
                for i in range(len(sonuclar['documents'][0])):
                    kanun = sonuclar['metadatas'][0][i]['kanun']
                    madde = sonuclar['metadatas'][0][i]['madde']
                    icerik = sonuclar['documents'][0][i]
                    baglam_metni += f"- {kanun} Madde {madde}: {icerik}\n"
            return baglam_metni
        except Exception:
            return ""

    @classmethod
    def yanit_uret(cls, api_key, mesaj_gecmisi, yeni_mesaj, mod="Özet"):
        try:
            genai.configure(api_key=api_key)
            
            # Güvenlik Ayarları
            guvenlik_ayarlari = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # --- 1. ADIM: KVKK MASKELEME ---
            guvenli_mesaj = cls.kvkk_maskele(yeni_mesaj)
            
            # --- 2. ADIM: RAG İLE LOKAL VERİTABANINDA ARAMA ---
            ilgili_mevzuat = cls._rag_baglami_getir(guvenli_mesaj)
            
            # --- 3. ADIM: SİSTEM PROMPTUNU HAZIRLAMA (RAG ENTEGRELİ) ---
            sistem_talimati = (
                "Sen JUNILEX'sin. Sadece Türk Hukuk Sistemine göre cevap veren kıdemli bir yapay zeka asistanısın. "
                "Eğer aşağıda 'İlgili Mevzuat Bağlamı' verilmişse, cevabını KESİNLİKLE öncelikle bu bağlama dayandır. "
                "Bağlamda cevap yoksa, genel hukuki bilgini kullan ancak ASLA kanun maddesi veya Yargıtay kararı uydurma.\n\n"
            )
            
            if ilgili_mevzuat:
                sistem_talimati += f"📌 İLGİLİ MEVZUAT BAĞLAMI:\n{ilgili_mevzuat}\n\n"

            # Modlara göre ek talimatlar
            if mod == "Özet":
                sistem_talimati += (
                    "Cevabını DOYURUCU bir şekilde şu 3 başlık altında detaylandırarak ver:\n"
                    "1. Olayın Hukuki Niteliği\n"
                    "2. İlgili Kanun Maddeleri\n"
                    "3. Muhtemel Sonuç ve Yargıtay Eğilimi"
                )
            elif mod == "Detaylı (Dilekçe Öncesi)":
                sistem_talimati += (
                    "Konuyu detaylı hukuki analize tabi tut. Yargıtay'ın yerleşik içtihat yönelimlerini, "
                    "hukuki dayanakları ve olası riskleri ayrı ayrı ele al."
                )

            yapilandirma = genai.types.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.7 # Halüsinasyonu azaltmak için 0.8'den 0.7'ye düşürüldü
            )

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=sistem_talimati,
                generation_config=yapilandirma,
                safety_settings=guvenlik_ayarlari
            )
            
            # Geçmişi hazırla
            gecmis_formatli = []
            for m in mesaj_gecmisi:
                rol = "user" if m["role"] == "user" else "model"
                gecmis_formatli.append({"role": rol, "parts": [m["content"]]})
            
            chat = model.start_chat(history=gecmis_formatli)
            
            # Maskelenmiş mesajı modele gönderiyoruz
            response = chat.send_message(guvenli_mesaj, stream=True)
            return response
            
        except Exception as e:
            raise Exception(f"ChatEngine Hatası: {str(e)}")
