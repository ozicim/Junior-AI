import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import chromadb
from sentence_transformers import SentenceTransformer

# RAG Motorunu Global Başlat
try:
    chroma_client = chromadb.PersistentClient(path="./junilex_vector_db")
    collection = chroma_client.get_or_create_collection(name="turk_mevzuati")
    embedding_model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
except Exception as e:
    print(f"Veritabanı başlatılırken hata: {e}")


class ChatEngine:

    @staticmethod
    def kvkk_maskele(metin):
        metin = re.sub(r"\b[1-9][0-9]{10}\b", "[TC_KİMLİK_GİZLENDİ]", metin)
        metin = re.sub(r"\b05\d{9}\b", "[TELEFON_GİZLENDİ]", metin)
        return metin

    @staticmethod
    def _uslup_analiz_et(mesaj_gecmisi):
        """Kullanıcının üslubunu analiz eder."""
        if not mesaj_gecmisi:
            return "Nötr"
        # Son 3 mesajın içeriğine bak
        son_mesajlar = " ".join([m["content"] for m in mesaj_gecmisi[-3:]]).lower()
        if any(
            kelime in son_mesajlar
            for kelime in ["hukuki", "içtihat", "doktrin", "müvekkil"]
        ):
            return "Akademik ve Resmi"
        elif any(
            kelime in son_mesajlar for kelime in ["basit", "özetle", "anlat", "nedir"]
        ):
            return "Pratik ve Açıklayıcı"
        return "Nötr"

    @staticmethod
    def _rag_baglami_getir(soru, max_sonuc=3):
        try:
            soru_vektoru = embedding_model.encode(soru).tolist()
            sonuclar = collection.query(
                query_embeddings=[soru_vektoru], n_results=max_sonuc
            )

            baglam_metni = ""
            if sonuclar and "documents" in sonuclar and sonuclar["documents"][0]:
                for i in range(len(sonuclar["documents"][0])):
                    kanun = sonuclar["metadatas"][0][i].get("kanun", "Bilinmeyen")
                    madde = sonuclar["metadatas"][0][i].get("madde", "")
                    icerik = sonuclar["documents"][0][i]
                    baglam_metni += f"- [{kanun} Madde {madde}]: {icerik}\n"
            return baglam_metni
        except Exception as e:
            return ""

    @classmethod
    def yanit_uret(
        cls,
        api_key,
        mesaj_gecmisi,
        yeni_mesaj,
        mod="Özet",
        aktif_belge_metni=None,
        manuel_uslup=None,
    ):
        try:
            genai.configure(api_key=api_key)

            # KVKK ve Güvenlik
            guvenlik_ayarlari = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            guvenli_mesaj = cls.kvkk_maskele(yeni_mesaj)
            ilgili_mevzuat = cls._rag_baglami_getir(guvenli_mesaj)

            # Üslup Belirleme (Manuel seçilmediyse otomatik algıla)
            uslup = (
                manuel_uslup
                if manuel_uslup and manuel_uslup != "Nötr"
                else cls._uslup_analiz_et(mesaj_gecmisi)
            )

            sistem_talimati = f"""
            Sen JUNILEX'sin. Kıdemli bir hukuk asistanısın. 
            ÜSLUP TERCİHİ: {uslup}. 
            (Eğer Akademik: Resmi dil kullan, kavramsal derinlik kat. Eğer Pratik: Sade, anlaşılır ve eylem odaklı ol.)
            
            GÖREVİN VE KURALLAR:
            1. Sadece Türk Hukuk Sistemine göre cevap ver.
            2. Her bilginin yanına mutlaka köşeli parantez içinde kaynak göster [Örn: TMK Madde 1].
            3. Bilmediğin konularda asla uydurma, "Hukuki olarak net bir düzenleme bulunmamaktadır" de.
            4. Karar numarası veya spesifik emsal uydurma.
            """

            if aktif_belge_metni:
                sistem_talimati += f"\n📌 AKTİF İNCELENEN BELGE:\n{aktif_belge_metni}\n"
            if ilgili_mevzuat:
                sistem_talimati += f"\n📌 İLGİLİ MEVZUAT:\n{ilgili_mevzuat}\n"

            # Temperature 0.2: Hukuki tutarlılık için düşük sıcaklık
            yapilandirma = genai.types.GenerationConfig(
                max_output_tokens=8192, temperature=0.2
            )

            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=sistem_talimati,
                generation_config=yapilandirma,
                safety_settings=guvenlik_ayarlari,
            )

            gecmis_formatli = [
                {
                    "role": ("user" if m["role"] == "user" else "model"),
                    "parts": [m["content"]],
                }
                for m in mesaj_gecmisi
            ]
            chat = model.start_chat(history=gecmis_formatli)

            return chat.send_message(guvenli_mesaj, stream=True)

        except Exception as e:
            raise Exception(f"ChatEngine Hatası: {str(e)}")
