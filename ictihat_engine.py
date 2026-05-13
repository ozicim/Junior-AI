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
            if not api_key:
                return "HATA: API Anahtarı eksik!"

            genai.configure(api_key=api_key)
            
            # --- HİBRİT ARAMA STRATEJİSİ ---
            # Önce arama motorlu modeli deniyoruz
            try:
                model = genai.GenerativeModel(
                    model_name='gemini-2.5-flash',
                    tools=[{"google_search_retrieval": {}}]
                )
                prompt = f"Aşağıdaki hukuki olay için internetten gerçek Yargıtay kararları ve kanun maddeleri bul: {olay_ozeti}"
                response = model.generate_content(prompt)
                return response.text
            except:
                # Eğer arama aracı hata verirse (yetki yoksa), normal moda düşüyoruz
                model = genai.GenerativeModel('gemini-2.5-flash')
                prompt = f"Sen bir Yargıtay hakimi gibi şu olayı analiz et. İnternete erişemiyorsan bile bildiğin gerçek kanun maddelerini (TBK, TMK vb.) ve yerleşik Yargıtay ilkelerini yaz: {olay_ozeti}"
                response = model.generate_content(prompt)
                return response.text

        except Exception as e:
            return f"HATA (Sistem): {str(e)}"
