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
            Sen uzman bir Yargıtay tetkik hakimi yardımcısısın. 
            Görevin, aşağıda verilen yargı kararını hukuki bir süzgeçten geçirmek ve sadece bu metne dayalı kalarak analiz yapmaktır.

            ⚠️ KRİTİK GÜVENLİK TALİMATLARI:
            1. SADECE sana verilen karar metnindeki bilgilere bağlı kal. 
            2. Karar metninde açıkça geçmeyen hiçbir vakıayı, maddeyi veya sonucu uydurma.
            3. Eğer kullanıcının sorusunun cevabı metinde yoksa, 'Söz konusu husus karar metninde yer almamaktadır' de ve uydurma bir yorum yapma.
            4. Karar metni dışındaki genel hukuk bilgilerini sadece metni açıklamak için kullan, yeni kararlar icat etme.

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
