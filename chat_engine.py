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
                "Sen JUNILEX CHAT'sin, Ozan Şahin Sicim tarafından hukuk öğrencileri ve avukatlar için geliştirilmiş "
                "üst düzey bir yapay zeka hukuk asistanısın. Hukuki terimleri doğru kullan, analizlerini "
                "Türk hukuk sistemine (TMK, TBK, TCK vb.) dayandır. Kesinlikle uydurma karar numarası verme. "
                "Profesyonel, yapıcı ve yardımsever bir üslup kullan. Kullanıcıya hitap ederken 'Ustam' veya "
                "saygılı bir hukukçu dili tercih et."
            )
            
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=sistem_talimati
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
