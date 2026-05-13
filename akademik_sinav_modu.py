import google.generativeai as genai
import json
import re

class AkademikSinavEngine:
    @classmethod
    def pratik_calisma_uret(cls, api_key, konu_adi, ders_notu_metni=None):
        try:
            genai.configure(api_key=api_key)
            # Model ismini güncel ve stabil olanla sabitledim
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            kaynak_bilgi = f"Ders Notu: {ders_notu_metni}" if ders_notu_metni else "Genel hukuk öğretisi."
            
            prompt = f"""
            Hukuk profesörü olarak {konu_adi} üzerine bir pratik çalışma (sınav) hazırla.
            Kaynak Bilgi: {kaynak_bilgi}
            
            GÖREVİN:
            - Bir olay kurgusu (vaka) oluştur.
            - Bu olayla ilgili çoktan seçmeli 3-4 soru hazırla.
            - Her sorunun doğru cevabını ve detaylı hukuki analizini ekle.
            
            ZORUNLU FORMAT (Sadece ham JSON döndür, başka açıklama yazma):
            {{
                "olay_kurgusu": "olay metni...",
                "sorular": [
                    {{
                        "soru": "soru metni...",
                        "secenekler": ["A şıkkı", "B şıkkı", "C şıkkı", "D şıkkı"],
                        "cevap": "Doğru şıkkın tam metni",
                        "analiz": "Hukuki gerekçe ve analiz..."
                    }}
                ]
            }}
            """
            
            # AI'dan cevabı alıyoruz
            response = model.generate_content(prompt)
            if not response or not response.text:
                return {"hata": "AI boş cevap döndürdü."}
                
            ham_yanit = response.text
            
            # 1. JSON TEMİZLEME: Markdown bloklarını ve gizli karakterleri temizliyoruz
            temiz_metin = re.sub(r'```json|```', '', ham_yanit).strip()
            temiz_metin = re.sub(r"[\x00-\x1F\x7F]", "", temiz_metin) # Gizli kontrol karakterleri
            
            # 2. JSON YÜKLEME
            try:
                sinav_verisi = json.loads(temiz_metin, strict=False)
                
                # Format kontrolü
                if "olay_kurgusu" not in sinav_verisi:
                    return {"hata": "AI uygun formatta sınav üretemedi, lütfen tekrar deneyin."}
                
                return sinav_verisi
                
            except json.JSONDecodeError as je:
                return {"hata": f"JSON Ayrıştırma Hatası: {str(je)}"}

        except Exception as e:
            # Hata mesajını güvenli bir şekilde dışarı aktarıyoruz
            return {"hata": f"Sistem Hatası: {str(e)}"}
