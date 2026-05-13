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
        """3 farklı koldan arama yaparak emsal yakalama şansını artırır."""
        url = "https://google.serper.dev/search"
        # Sadece olayı değil, 'Esas Karar No' gibi teknik kelimeleri de zorluyoruz.
        queries = [
            f"Yargıtay emsal karar Esas Karar No {query}",
            f"site:kararara.com {query} ispat yükü",
            f"site:barobirlik.org.tr {query} yargıtay kararı"
        ]
        
        combined_results = []
        for q in queries:
            payload = json.dumps({"q": q, "gl": "tr", "hl": "tr", "num": 5}) # Her sorgudan 5 sonuç
            headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
            response = requests.request("POST", url, headers=headers, data=payload)
            combined_results.extend(response.json().get('organic', []))
        
        return combined_results
    
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
            SEN BİR YARGITAY ANALİSTİSİN. 
            Arama sonuçlarında numara bulamasan bile ASLA 'boş bırakılmıştır' deme. 
            
            GÖREVİN:
            1. Eğer sonuçlarda numara VARSA, doğrudan onu yaz.
            2. Eğer numara YOKSA, internetten öğrendiğin bilgilerle 'Yargıtay 3. Hukuk Dairesi'nin yerleşik görüşü şudur...' diyerek doktrini açıkla.
            3. İspat yükünün kimde olduğunu kesin bir dille belirt (TBK 112 ve 382 vurgusuyla).
            4. Kullanıcıya bu kararı hangi anahtar kelimelerle (Örn: 'Ariyet hasarlı iade') araması gerektiğini söyle.
            
            OLAY: {olay_ozeti}
            ARAMA VERİLERİ: {context}
            """

            FORMAT:
            - **⚖️ Hukuki Dayanak:** (İlgili Kanun Maddesi)
            - **🔍 Gerçek Emsal:** (Arama sonuçlarındaki gerçek Daire ve Esas/Karar No)
            - **📢 Sonuç:** (Yargıtay'ın bu konudaki net tavrı)
            """
            
            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            return f"Operasyon Hatası: {str(e)}"
