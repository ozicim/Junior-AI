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

   
    import google.generativeai as genai


    @classmethod
    def emsal_ara(cls, api_key, olay_ozeti):
        try:
            if not api_key:
                return "HATA: API Anahtarı bulunamadı!"

            genai.configure(api_key=api_key)

            # --- Arama Aracını En Sade Haline Getirdik ---
            # Karmaşık ayarları sildik, sadece 'google_search_retrieval' bıraktık.
            tools = [{"google_search_retrieval": {}}]

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash', # 'models/gemini-1.5-flash' da denenebilir
                tools=tools
            )

            prompt = f"""
            Sen kıdemli bir Yargıtay tetkik hakimisin. 
            Aşağıdaki olayla ilgili internetten GERÇEK Yargıtay kararlarını ve kanun maddelerini bul.
            
            OLAY: {olay_ozeti}

            GÖREVİN:
            1. Bu olaya uyan TBK veya ilgili kanun maddelerini yaz.
            2. Google'da arayarak gerçek Esas ve Karar numaralı örnekler ver.
            3. İspat yükünün kimde olduğunu Yargıtay içtihatlarına göre açıkla.
            """

            # ÖNEMLİ: Stream'i kaldırıp deniyoruz (Hata tespiti için daha iyidir)
            response = model.generate_content(prompt)
            
            # Eğer yanıt boşsa (Bloklanmış olabilir)
            if not response.text:
                return "HATA: AI yanıt üretti ama içerik boş (Güvenlik filtresine takılmış olabilir)."
                
            return response.text # Stream yerine direkt metin döndürüyoruz

        except Exception as e:
            # Buradaki hata mesajı bize "API yetkisi mi yok" yoksa "Arama mı yapılamıyor" söyleyecek
            return f"HATA (Detaylı): {str(e)}"
