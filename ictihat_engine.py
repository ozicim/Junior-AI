import google.generativeai as genai
import requests
import json

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
    def serper_search(cls, query, api_key):
        """Serper.dev üzerinden Google araması yapar."""
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": f"site:kararara.com OR site:kazanci.com.tr OR site:leperas.com.tr {query}",
            "gl": "tr",
            "hl": "tr"
        })
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()

    @classmethod
    def emsal_ara(cls, gemini_key, serper_key, olay_ozeti):
        try:
            # 1. Arama Yap (Hukuk odaklı sitelerde)
            search_results = cls.serper_search(olay_ozeti, serper_key)
            
            # 2. Arama sonuçlarından metinleri ayıkla
            context = ""
            for result in search_results.get('organic', []):
                context += f"\nBaşlık: {result.get('title')}\nÖzet: {result.get('snippet')}\nLink: {result.get('link')}\n"

            # 3. Gemini'a veriyi "kanıt" olarak sun
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            Aşağıdaki arama sonuçlarını kullanarak bir Yargıtay analizi yap. 
            SADECE sağlanan bilgilerdeki gerçek Esas/Karar numaralarını kullan. 
            Uydurma veri üretme!

            ARAMA SONUÇLARI:
            {context}

            OLAY: {olay_ozeti}

            FORMAT:
            - **⚖️ Hukuki Dayanak:** (İlgili Kanun Maddesi)
            - **🔍 Gerçek Emsal:** (Arama sonuçlarındaki gerçek Daire ve Esas/Karar No)
            - **📢 Sonuç:** (Yargıtay'ın bu konudaki net tavrı)
            """
            
            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            return f"Operasyon Hatası: {str(e)}"
