import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import chromadb
from sentence_transformers import SentenceTransformer

# RAG Motorunu Global Başlat
try:
    chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
    collection = chroma_client.get_or_create_collection(name="turk_mevzuati")
    embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
except Exception as e:
    print(f"Veritabanı başlatılırken hata: {e}")

class ChatEngine:

    @staticmethod
    def kvkk_maskele(metin):
        metin = re.sub(r'\b[1-9][0-9]{10}\b', '[TC_KİMLİK_GİZLENDİ]', metin)
        metin = re.sub(r'\b05\d{9}\b', '[TELEFON_GİZLENDİ]', metin)
        return metin

    @staticmethod
    def _rag_baglami_getir(soru, max_sonuc=3):
        try:
            soru_vektoru = embedding_model.encode(soru).tolist()
            sonuclar = collection.query(
                query_embeddings=[soru_vektoru],
                n_results=max_sonuc
            )
            
            baglam_metni = ""
            if sonuclar and 'documents' in sonuclar and sonuclar['documents'][0]:
                for i in range(len(sonuclar['documents'][0])):
                    kanun = sonuclar['metadatas'][0][i].get('kanun', 'Bilinmeyen Kanun')
                    madde = sonuclar['metadatas'][0][i].get('madde', '')
                    icerik = sonuclar['documents'][0][i]
                    baglam_metni += f"- {kanun} Madde {madde}: {icerik}\n"
            return baglam_metni
        except Exception as e:
            print(f"RAG Hatası: {e}")
            return ""

    @classmethod
    def yanit_uret(cls, api_key, mesaj_gecmisi, yeni_mesaj, mod="Özet", aktif_belge_metni=None):
        try:
            genai.configure(api_key=api_key)
            
            guvenlik_ayarlari = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            guvenli_mesaj = cls.kvkk_maskele(yeni_mesaj)
            ilgili_mevzuat = cls._rag_baglami_getir(guvenli_mesaj)
            
            sistem_talimati = "Sen JUNILEX'sin. Sadece Türk Hukuk Sistemine göre cevap veren kıdemli bir yapay zeka asistanısın."
            
            if aktif_belge_metni:
                sistem_talimati += f"\n📌 AKTİF İNCELENEN BELGE İÇERİĞİ:\n{aktif_belge_metni}\n"
            
            if ilgili_mevzuat:
                sistem_talimati += f"\n📌 İLGİLİ MEVZUAT BAĞLAMI:\n{ilgili_mevzuat}\n"

            if mod == "Özet":
                sistem_talimati += "\nCevabını 1. Olayın Hukuki Niteliği, 2. İlgili Kanun Maddeleri, 3. Muhtemel Sonuç şeklinde ver."
            elif mod == "⚖️ Detaylı Analiz":
                sistem_talimati += "\nKonuyu detaylı hukuki analize tabi tut. Yargıtay'ın yerleşik içtihat yönelimlerini ele al."

            yapilandirma = genai.types.GenerationConfig(max_output_tokens=8192, temperature=0.7)
            
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                system_instruction=sistem_talimati,
                generation_config=yapilandirma,
                safety_settings=guvenlik_ayarlari
            )
            
            gecmis_formatli = [{"role": ("user" if m["role"] == "user" else "model"), "parts": [m["content"]]} for m in mesaj_gecmisi]
            
            chat = model.start_chat(history=gecmis_formatli)
            return chat.send_message(guvenli_mesaj, stream=True)
            
        except Exception as e:
            raise Exception(f"ChatEngine Hatası: {str(e)}")
