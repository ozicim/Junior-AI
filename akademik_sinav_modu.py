import google.generativeai as genai
import json
import re
import os
import zipfile
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

class AkademikSinavEngine:
    @classmethod
    def pratik_calisma_uret(cls, api_key, konu_adi, ders_notu_metni, sinav_tipi, soru_sayisi):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.0-flash')
            
            # --- FAISS RAG Kısmı (Aynı kalıyor) ---
            kaynak_bilgi = f"Öğrencinin Notu:\n{ders_notu_metni}" if ders_notu_metni else "Akademik Arşiv:"
            if not ders_notu_metni:
                # [FAISS Arama Mantığı buraya gelecek...]
                pass

            prompt = f"""
            SEN KIDEMLİ BİR HUKUK PROFESÖRÜSÜN.
            {konu_adi} konusunda {soru_sayisi} adet {sinav_tipi} sınav hazırla.
            
            GÖREVİN:
            - Olay kurgusu oluştur.
            - {sinav_tipi} formatında sorular hazırla.
            - Her sorunun cevabını ve "analiz" (klasikse çözüm yolu, testse açıklama) kısmını ekle.
            
            ZORUNLU FORMAT (JSON):
            {{
                "olay_kurgusu": "...",
                "sorular": [
                    {{"soru": "...", "secenekler": ["..."], "cevap": "...", "analiz": "..."}}
                ]
            }}
            """
            response = model.generate_content(prompt)
            return json.loads(re.sub(r'```json|```', '', response.text).strip())
        except Exception as e:
            return {"hata": str(e)}

    @classmethod
    def sinav_degerlendir(cls, api_key, soru, ogrenci_cevabi, dogru_analiz):
        """Klasik sınavı 100 üzerinden puanlar."""
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.0-flash')
            
            prompt = f"""
            Hukuk profesörü olarak öğrencinin cevabını puanla.
            Soru: {soru}
            Öğrencinin Cevabı: {ogrenci_cevabi}
            Doğru Yanıt/Analiz Kriteri: {dogru_analiz}
            
            ZORUNLU JSON FORMATI:
            {{"puan": 0-100, "gercekce": "Neden kırdın? Hangi hukuki kavram eksik?"}}
            """
            response = model.generate_content(prompt)
            return json.loads(re.sub(r'```json|```', '', response.text).strip())
        except Exception as e:
            return {"puan": 0, "gercekce": f"Değerlendirme hatası: {str(e)}"}
