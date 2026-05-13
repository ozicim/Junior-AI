import google.generativeai as genai
import requests
import json

class IctihatEngine:
    @classmethod
    def karar_analiz_et(cls, api_key, karar_metni, soru):
        """
        Yüksek yargı kararlarını analiz eder.
        """
        try:
            genai.configure(api_key=api_key)
            
            generation_config = {
                "temperature": 0,
                "top_p": 0.1,
                "top_k": 1,
            }
            
            model = genai.GenerativeModel(
                model_name='gemini-3-flash',
                generation_config=generation_config
            )

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

            response = model.generate_content(prompt, stream=True)
            return response

        except Exception as e:
            return f"İçtihat analizi sırasında bir usul hatası oluştu: {str(e)}"

    @classmethod
    def serper_search(cls, query, api_key):
        """Serper.dev üzerinden Google araması yapar."""
        url = "https://google.serper.dev/search"
        # Sorguyu hukuk odaklı ve numara bulmaya zorlayacak şekilde genişlettik
        payload = json.dumps({
            "q": f"site:kararara.com OR site:kazanci.com.tr OR site:leperas.com.tr {query} emsal karar esas karar no",
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
            model = genai.GenerativeModel('gemini-3-flash')
            
            # PROMPT DÜZELTİLDİ: Tırnaklar ve format birleştirildi
            prompt = f"""
            SEN BİR YARGITAY ANALİSTİSİN. 
            Arama sonuçlarında numara bulamasan bile ASLA 'boş bırakılmıştır' deme. 
            
            GÖREVİN:
            1. Eğer sonuçlarda numara VARSA, doğrudan onu yaz.
            2. Eğer numara YOKSA, internetten öğrendiğin bilgilerle 'Yargıtay 3. Hukuk Dairesi'nin yerleşik görüşü şudur...' diyerek doktrini açıkla.
            3. İlgili kanun maddelerini (TKHK m. 11, TBK m. 227 vb.) mutlaka belirt.
            
            OLAY: {olay_ozeti}
            ARAMA VERİLERİ: {context}

            FORMAT:
            - **⚖️ Hukuki Dayanak:** (İlgili Kanun Maddesi ve İçeriği)
            - **🔍 Gerçek Emsal:** (Arama sonuçlarındaki Daire ve Esas/Karar No)
            - **📢 Sonuç ve Tavsiye:** (Yargıtay'ın bu konudaki net tavrı ve izlenmesi gereken yol)
            """
            
            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            return f"Operasyon Hatası: {str(e)}"
