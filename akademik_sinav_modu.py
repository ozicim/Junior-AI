import google.generativeai as genai
import json
import re


class AkademikSinavEngine:

    @classmethod
    def _modeli_hazirla(cls, api_key):
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("models/gemini-2.5-flash")

    @classmethod
    def pratik_calisma_uret(
        cls, api_key, konu_adi, ders_notu_metni, sinav_tipi, soru_sayisi
    ):
        try:
            model = cls._modeli_hazirla(api_key)

            prompt = f"""
            SEN KIDEMLİ BİR HUKUK PROFESÖRÜSÜN.
            {konu_adi} konusunda {soru_sayisi} adet {sinav_tipi} sınav hazırla.
            
            KAYNAK DERS NOTU:
            {ders_notu_metni if ders_notu_metni else "Genel akademik müfredat kurgusu."}

            GÖREVİN:
            - Hukuki bir olay kurgusu (olay metni) oluştur.
            - {sinav_tipi} formatında sorular hazırla.
            - Her sorunun cevabını ve detaylı analizini (çözüm yolu/gerekçesi) ekle.
            
            SADECE GEÇERLİ BİR JSON YANITI DÖN. FORMAT:
            {{
                "olay_kurgusu": "...",
                "sorular": [
                    {{
                        "soru": "...",
                        "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                        "cevap": "...",
                        "analiz": "..."
                    }}
                ]
            }}
            """
            response = model.generate_content(
                prompt, generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            return {"hata": f"Pratik çalışma üretilemedi: {str(e)}"}

    @classmethod
    def sinav_degerlendir(cls, api_key, soru, ogrenci_cevabi, dogru_analiz):
        """Klasik sınavı 100 üzerinden puanlar."""
        try:
            model = cls._modeli_hazirla(api_key)

            prompt = f"""
            Hukuk profesörü olarak öğrencinin cevabını puanla.
            Soru: {soru}
            Öğrencinin Cevabı: {ogrenci_cevabi}
            Doğru Yanıt/Analiz Kriteri: {dogru_analiz}
            
            SADECE GEÇERLİ BİR JSON YANITI DÖN. FORMAT:
            {{
                "puan": 85,
                "gercekce": "Neden puan kırdın? Hangi hukuki kavram eksik veya doğru?"
            }}
            """
            response = model.generate_content(
                prompt, generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            return {"puan": 0, "gercekce": f"Değerlendirme hatası: {str(e)}"}
