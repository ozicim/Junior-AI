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
                model_name='gemini-2.5-flash', # Stabil versiyon
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
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # PROMPT: Artik spesifik karar numaralari istiyoruz
            prompt = f"""
            Sen Yargıtay yayınlarını ezbere bilen kıdemli bir hukukçusun. 
            Aşağıdaki olayı analiz et ve bu konuda verilmiş gerçek emsal kararlara atıf yap.

            OLAY: {olay_ozeti}

            GÖREVİN:
            Aşağıdaki formatta, hukuki terminolojiye uygun bir "Emsal Notu" hazırla:

            1. **⚖️ Hukuki Teşhis:** Olayın kanuni niteliği (Örn: TBK m. 379 - Kullanım Ödüncü).
            2. **🔍 Emsal Karar Atıfları:** Bu konuda karar vermiş Yargıtay Dairelerini (Örn: 3. HD, 13. HD vb.) ve varsa örnek Esas/Karar numaralarını belirt.
            3. **📌 Karar Özeti:** Yargıtay'ın bu tip olaylarda ispat yükü ve kusur konusundaki yerleşik içtihadını açıkla.
            4. **📢 Netice:** Müvekkilin haklılık durumunu bu içtihatlar ışığında yorumla.
            """
            
            response = model.generate_content(prompt, stream=True)
            return response
        except Exception as e:
            return f"HATA: {str(e)}"
