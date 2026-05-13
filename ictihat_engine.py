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
        """
        Google Search Tool kullanarak gerçek içtihat ve kanun maddesi bulur.
        """
        try:
            if not api_key:
                return "HATA: API Anahtarı eksik!"

            genai.configure(api_key=api_key)

            # --- DİKKAT: Google Search Tool'u tanımlıyoruz ---
            # Bu araç Gemini'ın internete çıkıp gerçek verileri taramasını sağlar.
            tools = [
                {
                    "google_search_retrieval": {
                        "dynamic_retrieval_config": {
                            "mode": "unspecified",
                            "dynamic_threshold": 0.06 # Düşük eşik = Daha çok arama
                        }
                    }
                }
            ]

            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                tools=tools # Arama motorunu buraya bağladık!
            )

            # PROMPT: Artik spesifik ve belgeli veri istiyoruz
            prompt = f"""
            Sen profesyonel bir Yargıtay Tetkik Hakimisin. Aşağıdaki olayı gerçek dünya verileriyle analiz et.
            
            GÖREVİN:
            1. İnterneti tarayarak bu olayla birebir örtüşen GERÇEK Yargıtay Esas/Karar numaralarını bul.
            2. Olayın dayandığı temel Türk Kanun maddelerini (TBK, TMK vb.) içeriğiyle birlikte getir.
            3. Verileri şu formatta (Kitap Şerhi gibi) sun:

            ---
            ### ⚖️ HUKUKİ TEŞHİS VE MEVZUAT
            - **İlgili Kanun Maddesi:** (Örn: TBK m. 379 ve açıklaması)
            - **Hukuki Niteleme:** (Olayın hukuki tanımı)

            ### 🔍 GERÇEK EMSAL KARARLAR (Google Arama Destekli)
            - **Karar 1:** (Daire Adı, Esas/Karar No, Karar Yılı)
            - **Karar Özeti:** (Yargıtay'ın bu olaydaki kritik ispat yükü yorumu)
            - **Kaynak:** (Bulduğun internet sitesinin adı veya linki)

            ### 📌 YARGITAY'IN KIRMIZI ÇİZGİSİ
            - Mahkemelerin bu durumda asla taviz vermediği ana ilke nedir?
            ---

            OLAY: {olay_ozeti}
            """

            # Akış (Streaming) başlatılıyor
            response = model.generate_content(prompt, stream=True)
            return response

        except Exception as e:
            return f"HATA: Motor internete bağlanırken bir sorun yaşadı: {str(e)}"
