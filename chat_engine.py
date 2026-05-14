import google.generativeai as genai

class ChatEngine:
    @classmethod
    def yanit_uret(cls, api_key, mesaj_gecmisi, yeni_mesaj, mod="Özet"):
        try:
            genai.configure(api_key=api_key)
            
            # --- MODA GÖRE PERSONA VE AYARLAR ---
            if mod == "Özet":
                sistem_talimati = (
                    "Sen JUNILEX'sin. Samimi, yardımsever ve pratik bir hukukçu dost gibi davran. "
                    "Görevin sorulara kısa, net ve doğrudan cevap vermektir. "
                    "Resmi mütalaa formatından kaçın, sanki bir arkadaşına hızlıca bilgi veriyormuşsun gibi yaz."
                    "Sakın karar uydurma."
                )
                yapilandirma = {"max_output_tokens": 1000, "temperature": 0.5}
            else: # Detay Modu
                sistem_talimati = (
                    "Sen JUNILEX'sin. Bilgili ama çok samimi bir hukukçu dost gibi davran. "
                    "Meseleyi derinlemesine anlat ama sakın akademik 'mütalaa' formatına girme. "
                    "Ağır hukuk terimlerini günlük dille harmanla. Sanki karşılıklı kahve içiyormuşuz gibi "
                    "detayları, riskleri ve kanun maddelerini anlat. 'Giriş', 'Sonuç' gibi başlıklar kullanma, "
                    "akıcı bir sohbet diliyle yaz."
                    "Sakın karar uydurma."
                )
                yapilandirma = {"max_output_tokens": 2000, "temperature": 0.8}

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash', # Hız için flash, derinlik için gerekirse pro
                system_instruction=sistem_talimati,
                generation_config=yapilandirma
            )
            
            # Geçmişi hazırla
            gecmis_formatli = []
            for m in mesaj_gecmisi:
                rol = "user" if m["role"] == "user" else "model"
                gecmis_formatli.append({"role": rol, "parts": [m["content"]]})
            
            chat = model.start_chat(history=gecmis_formatli)
            return chat.send_message(yeni_mesaj, stream=True)
            
        except Exception as e:
            return f"HATA: {str(e)}"
