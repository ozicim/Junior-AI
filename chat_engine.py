import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import chromadb
from sentence_transformers import SentenceTransformer

# RAG Motorunu Global Başlat
# (Dosya yüklendiğinde bir kez başlatılması yeterlidir)
try:
    chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
    collection = chroma_client.get_or_create_collection(name="turk_mevzuati")
    embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
except Exception as e:
    print(f"Veritabanı başlatılırken hata: {e}")

class ChatEngine:

    @staticmethod
    def kvkk_maskele(metin):
        """Metin içindeki TC ve Telefon numaralarını maskeler."""
        # 11 Haneli TC Kimlik Numarası
        metin = re.sub(r'\b[1-9][0-9]{10}\b', '[TC_KİMLİK_GİZLENDİ]', metin)
        # 05 ile başlayan telefon numarası
        metin = re.sub(r'\b05\d{9}\b', '[TELEFON_GİZLENDİ]', metin)
        return metin

    @staticmethod
    def _rag_baglami_getir(soru, max_sonuc=3):
        """Kullanıcının sorusuna en uygun kanun maddelerini ChromaDB'den çeker."""
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
            
            # 1. KVKK Maskeleme
            guvenli_mesaj = cls.kvkk_maskele(yeni_mesaj)
            
            # 2. RAG Mevzuat Bağlamı
            ilgili_mevzuat = cls._rag_baglami_getir(guvenli_mesaj)
            
            # 3. Sistem Talimatı (Prompt Mühendisliği)
            sistem_talimati = (
                "Sen JUNILEX'sin. Sadece Türk Hukuk Sistemine göre cevap veren kıdemli bir yapay zeka asistanısın. "
            )
            
            # Aktif belge metni varsa ekle
            if aktif_belge_metni:
                sistem_talimati += f"\n📌 AKTİF İNCELENEN BELGE İÇERİĞİ:\n{aktif_belge_metni}\n"
            
            # Mevzuat bağlamı varsa ekle
            if ilgili_mevzuat:
                sistem_talimati += f"\n📌 İLGİLİ MEVZUAT BAĞLAMI:\n{ilgili_mevzuat}\n"

            # Mod yönetimi
            if mod == "Özet":
                sistem_talimati += "\nCevabını 1. Olayın Hukuki Niteliği, 2. İlgili Kanun Maddeleri, 3. Muhtemel Sonuç şeklinde ver."
            elif mod == "⚖️ Detaylı Analiz":
                sistem_talimati += "\nKonuyu detaylı hukuki analize tabi tut. Yargıtay'ın yerleşik içtihat yönelimlerini ele al."

            yapilandirma = genai.types.GenerationConfig(
                max_output_tokens=8192, 
                temperature=0.7
            )
            
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash', # Model versiyonunu güncelledim
                system_instruction=sistem_talimati,
                generation_config=yapilandirma,
                safety_settings=guvenlik_ayarlari
            )
            
            # Geçmişi hazırla
            gecmis_formatli = [{"role": ("user" if m["role"] == "user" else "model"), "parts": [m["content"]]} for m in mesaj_gecmisi]
            
            chat = model.start_chat(history=gecmis_formatli)
            return chat.send_message(guvenli_mesaj, stream=True)
            
        except Exception as e:
            raise Exception(f"ChatEngine Hatası: {str(e)}")
