import google.generativeai as genai

class ChatEngine:
    @classmethod
    def yanit_uret(cls, api_key, mesaj_gecmisi, yeni_mesaj):
        """
        Gemini API'yi kullanarak hafızalı bir sohbet yanıtı üretir.
        """
        try:
            genai.configure(api_key=api_key)
            
            # JUNILEX Personası: Kim olduğunu ve nasıl davranacağını burada tanımlıyoruz
            sistem_talimati = (
                
                "Sen JUNILEX CHAT'sin. Ozan Şahin Sicim tarafından geliştirilmiş kıdemli bir hukuk asistanısın. "
                "KRİTİK KURAL: Cevapların kısa, öz ve doğrudan olmalı. Gereksiz giriş-çıkış cümlelerinden kaçın. "
                "Hukuki analizi yaparken lafı uzatmadan en önemli maddeleri ve sonucu söyle. "
                "Mümkünse maddeleme (bullet points) kullan. "
                "Kesinlikle uydurma karar numarası verme. Profesyonel ama net bir dil kullan."
                "

            )
            
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=sistem_talimati
                generation_config={
                    "max_output_tokens": 600, 
                    "temperature": 0.7, # Bir tık daha odaklanmış cevaplar için
    }
            )
            
            # Streamlit geçmişini Gemini'nin anladığı 'history' formatına çeviriyoruz
            gecmis_formatli = []
            for m in mesaj_gecmisi:
                # Gemini 'assistant' yerine 'model' rolünü kullanır
                rol = "user" if m["role"] == "user" else "model"
                gecmis_formatli.append({"role": rol, "parts": [m["content"]]})
            
            # Sohbeti başlat ve yanıtı akış (stream) olarak al
            chat = model.start_chat(history=gecmis_formatli)
            response = chat.send_message(yeni_mesaj, stream=True)
            
            return response
            
        except Exception as e:
            return f"HATA: {str(e)}"
