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
            
            guvenli_mesaj = cls.kvkk_maskele(yeni_mesaj)
            ilgili_mevzuat = cls._rag_baglami_getir(guvenli_mesaj)
            
            # --- SİSTEM TALİMATI GÜNCELLEMESİ ---
            sistem_talimati = (
                "Sen JUNILEX'sin. Sadece Türk Hukuk Sistemine göre cevap veren kıdemli bir yapay zeka asistanısın. "
            )
            
            if aktif_belge_metni:
                sistem_talimati += f"\n📌 AKTİF İNCELENEN BELGE İÇERİĞİ:\n{aktif_belge_metni}\n"
            
            if ilgili_mevzuat:
                sistem_talimati += f"\n📌 İLGİLİ MEVZUAT BAĞLAMI:\n{ilgili_mevzuat}\n"

            # Mod yönetimi...
            if mod == "Özet":
                sistem_talimati += "\nCevabını 1. Olayın Hukuki Niteliği, 2. İlgili Kanun Maddeleri, 3. Muhtemel Sonuç şeklinde ver."
            elif mod == "⚖️ Detaylı Analiz":
                sistem_talimati += "\nKonuyu detaylı hukuki analize tabi tut. Yargıtay'ın yerleşik içtihat yönelimlerini ele al."

            yapilandirma = genai.types.GenerationConfig(max_output_tokens=8192, temperature=0.7)
            
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=sistem_talimati,
                generation_config=yapilandirma,
                safety_settings=guvenlik_ayarlari
            )
            
            gecmis_formatli = [{"role": ("user" if m["role"] == "user" else "model"), "parts": [m["content"]]} for m in mesaj_gecmisi]
            chat = model.start_chat(history=gecmis_formatli)
            return chat.send_message(guvenli_mesaj, stream=True)
            
        except Exception as e:
            raise Exception(f"ChatEngine Hatası: {str(e)}")
