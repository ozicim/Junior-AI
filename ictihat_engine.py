import google.generativeai as genai

class IctihatEngine:
    @classmethod
    def karar_analiz_et(cls, api_key, karar_metni, soru):
        """
        Yüksek yargı kararlarını sıfır halüsinasyon politikasıyla analiz eder.
        """
        try:
            genai.configure(api_key=api_key)
            
            # GÜVENLİK ÖNLEMİ 1: Generation Config
            # Temperature'ı 0 yaparak AI'nın yaratıcılığını öldürüyor, 
            # sadece gerçeklere sadık kalmasını sağlıyoruz.
            generation_config = {
                "temperature": 0,
                "top_p": 0.1,
                "top_k": 1,
            }
            
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash', # Uzun metinlerde Pro modeli daha tutarlıdır
                generation_config=generation_config
            )

            # GÜVENLİK ÖNLEMİ 2: Sertleştirilmiş Prompt
           prompt = f"""
           Sen bir Yargıtay Tetkik Hakimisin. Aşağıdaki olayı en kısa ve öz şekilde analiz et. 
           SADECE şu 3 başlığı kullan ve her birini maksimum 2-3 cümleyle açıkla:
           1. **⚖️ Hukuki Teşhis:** Olayın kanundaki tam karşılığı.
           2. **📌 Yargıtay'ın Kırmızı Çizgisi:** Bu konuda asla taviz verilmeyen ana ilke.
           3. **🔍 Emsal Yaklaşım:** Mahkemelerin bu durumda verdiği standart karar ve gerekçesi.
           OLAY: {olay_ozeti}
           """

            KARAR METNİ:
            {karar_metni}

            ANALİZ EDİLECEK SORU:
            {soru}

            ANALİZ ŞABLONU:
            - **Kararın Kısa Özeti:** (2-3 cümle)
            - **Hukuki Uyuşmazlık:** (Davanın temelindeki tartışma nedir?)
            - **Mahkemenin Gerekçesi:** (Hangi kanun maddelerine ve ilkelere dayandı? Metinden alıntı yaparak açıkla.)
            - **Netice:** (Onama mı, Bozma mı, İptal mi?)
            - **Soruya Yanıt:** (Kullanıcının sorusuna doğrudan, metne dayalı cevap.)
            """

            # Akış (Streaming) başlatılıyor
            response = model.generate_content(prompt, stream=True)
            return response

        except Exception as e:
            return f"İçtihat analizi sırasında bir usul hatası oluştu: {str(e)}"
    @classmethod
    def emsal_ara(cls, api_key, olay_ozeti):
        """
        Kullanıcının anlattığı olaya benzer emsal kararları bulur.
        """
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Soru sormadan direkt olay üzerinden emsal bulma talimatı
            prompt = f"""
            Sen kıdemli bir Yargıtay tetkik hakimisin. Sana anlatılan olaya benzer yerleşik içtihatları bul.
            
            OLAY: {olay_ozeti}
            
            GÖREVİN (Kitap formatında hazırla):
            1. **⚖️ HUKUKİ NİTELEME**: Olayın hukuki tanımını yap.
            2. **📌 YERLEŞİK İÇTİHAT**: Yargıtay'ın bu konudaki genel duruşu.
            3. **🔍 EMSAL KARARLAR**: Bilinen dosya numaraları ve daireler.
            4. **📝 MAHKEME GEREKÇESİ**: Kararlarda geçen temel hukuki mantık.
            5. **⚖️ NETİCE-İ TALEP**: Bu olayda izlenmesi gereken hukuki yol.
            """
            
            response = model.generate_content(prompt, stream=True)
            return response
        except Exception as e:
            return [f"Emsal arama hatası: {str(e)}"]
