import google.generativeai as genai

class IctihatEngine:
    @classmethod
    def karar_analiz_et(cls, api_key, karar_metni, soru):
        """
        Yüksek yargı kararlarını sıfır halüsinasyon politikasıyla analiz eder.
        """
        try:
            genai.configure(api_key=api_key)
            
            # GÜVENLİK ÖNLEMİ: Sadece gerçeklere sadık kalması için temperature 0
            generation_config = {
                "temperature": 0,
                "top_p": 0.1,
                "top_k": 1,
            }
            
            model = genai.GenerativeModel(
                model_name='gemini-1.5-flash', # Stabil versiyon
                generation_config=generation_config
            )

            # PROMPT DÜZELTİLDİ: Tüm metin tek bir f-string içine alındı
            prompt = f"""
            Sen kıdemli bir Yargıtay Tetkik Hakimisin. Aşağıdaki hukuk metnini analiz et.
            
            KARAR METNİ:
            {karar_metni}

            ANALİZ EDİLECEK SORU:
            {soru}

            GÖREVİN:
            Sadece aşağıdaki başlıklarla, kısa ve öz (maksimum 2-3 cümle) cevap ver:
            - **📄 Karar Özeti:** Kararın can alıcı noktası.
            - **⚖️ Hukuki Uyuşmazlık:** Davanın temelindeki tartışma.
            - **🏛️ Mahkeme Gerekçesi:** Kararın dayandığı temel kanun veya ilke.
            - **📢 Soruya Yanıt:** Kullanıcının sorusuna metne dayalı net cevap.
            """

            # Akış (Streaming) başlatılıyor
            response = model.generate_content(prompt, stream=True)
            return response

        except Exception as e:
            return f"İçtihat analizi sırasında bir usul hatası oluştu: {str(e)}"

    @classmethod
    def emsal_ara(cls, api_key, olay_ozeti):
        """
        Kullanıcının anlattığı olaya benzer yerleşik içtihat yaklaşımlarını bulur.
        """
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # PROMPT GÜNCELLEME: Kısa ve öz "Özet Kart" formatı
            prompt = f"""
            Sen kıdemli bir Yargıtay tetkik hakimisin. Aşağıdaki olayı en kısa ve öz şekilde analiz et. 
            SADECE şu 3 başlığı kullan ve her birini maksimum 2-3 cümleyle açıkla:

            1. **⚖️ Hukuki Teşhis:** Olayın kanundaki tam karşılığı ve ilgili madde.
            2. **📌 Yargıtay'ın Kırmızı Çizgisi:** Bu konuda asla taviz verilmeyen ana ilke.
            3. **🔍 Emsal Yaklaşım:** Mahkemelerin bu durumda verdiği standart karar ve gerekçesi.

            OLAY: {olay_ozeti}
            """
            
            response = model.generate_content(prompt, stream=True)
            return response
            
        except Exception as e:
            # Hata durumunda boş bir liste yerine hata mesajı döndüren generator yapısı
            return f"Emsal arama hatası: {str(e)}"
