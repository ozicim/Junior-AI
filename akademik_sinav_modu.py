import google.generativeai as genai
import json
import re

class AkademikSinavEngine:
    @classmethod
    def pratik_calisma_uret(cls, api_key, konu_adi, ders_notu_metni=None):
        try:
            genai.configure(api_key=api_key)
            
            
            kaynak_bilgi = f"Ders Notu: {ders_notu_metni[:5000]}" if ders_notu_metni else "Genel hukuk öğretisi."
            
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
            # Markdown temizliği (```json ... ``` bloklarını kaldırır)
            temiz_metin = response.text.replace("```json", "").replace("```", "").strip()
            
            json_match = re.search(r'\{.*\}', temiz_metin, re.DOTALL)
            if json_match:
                veriler = json.loads(json_match.group())
                # Anahtar kontrolü: Eğer AI anahtarı yanlış yazdıysa düzeltme veya hata fırlatma
                if "olay_kurgusu" not in veriler:
                    return {"hata": "AI formatı bozdu, lütfen tekrar deneyin."}
                return veriler
            return {"hata": "JSON formatı bulunamadı."}
        except Exception as e:
            return {"hata": str(e)}
