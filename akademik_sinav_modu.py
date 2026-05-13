import google.generativeai as genai
import json
import re

class AkademikSinavEngine:
    @classmethod
    def pratik_calisma_uret(cls, api_key, konu_adi, ders_notu_metni=None):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            
            kaynak_bilgi = f"Ders Notu: {ders_notu_metni}" if ders_notu_metni else "Genel hukuk öğretisi."
            
            prompt = f"""
            Hukuk profesörü olarak {konu_adi} üzerine bir sınav hazırla.
            Kaynak: {kaynak_bilgi}
            
            ZORUNLU FORMAT (Sadece JSON döndür):
            {{
                "olay_kurgusu": "olay metni...",
                "sorular": [
                    {{
                        "soru": "soru...",
                        "secenekler": ["A", "B", "C", "D"],
                        "cevap": "doğru şıkkın metni",
                        "analiz": "nedeni..."
                    }}
                ]
            }}
            """
            
            response = model.generate_content(prompt)
        def temiz_json_yukle(ham_metin):
            try:
            # 1. Eğer AI cevabı ```json ... ``` blokları içine aldıysa onları temizleyelim
            temiz_metin = re.sub(r'```json|```', '', ham_metin).strip()
        
            # 2. JSON içindeki kontrol karakterlerini (hataya sebep olan gizli karakterleri) temizleyelim
            # Bu satır, 0-31 arası kontrol karakterlerini temizler
            temiz_metin = re.sub(r"[\x00-\x1F\x7F]", "", temiz_metin)
        
            # 3. strict=False kullanarak yükleyelim (Bu en kritik hamle!)
            return json.loads(temiz_metin, strict=False)
        except Exception as e:
            print(f"JSON Ayıklama Hatası: {e}")
            return None
            if json_match:
                veriler = json.loads(json_match.group())
                # Anahtar kontrolü: Eğer AI anahtarı yanlış yazdıysa düzeltme veya hata fırlatma
                if "olay_kurgusu" not in veriler:
                    return {"hata": "AI formatı bozdu, lütfen tekrar deneyin."}
                return veriler
            return {"hata": "JSON formatı bulunamadı."}
        except Exception as e:
            return {"hata": str(e)}
