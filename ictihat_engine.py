import google.generativeai as genai
import requests
import json

class IctihatEngine:
    @classmethod
    def karar_analiz_et(cls, api_key, karar_metni, soru):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-pro')
            prompt = f"""
            Sen kıdemli bir Yargıtay Tetkik Hakimisin. Aşağıdaki hukuk metnini analiz et.
            KARAR METNİ: {karar_metni}
            ANALİZ EDİLECEK SORU: {soru}
            GÖREVİN:
            Sadece aşağıdaki başlıklarla cevap ver:
            - **📄 Karar Özeti**
            - **⚖️ Hukuki Uyuşmazlık**
            - **🏛️ Mahkeme Gerekçesi**
            - **📢 Soruya Yanıt**
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"HATA: {str(e)}"

    @classmethod
    def serper_search(cls, query, api_key):
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": f"site:kararara.com OR site:kazanci.com.tr {query} emsal karar",
            "gl": "tr", "hl": "tr"
        })
        headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    
    @classmethod
    def emsal_ara(cls, gemini_key, serper_key, olay_ozeti):
        try:
            search_results = cls.serper_search(olay_ozeti, serper_key)
            context = ""
            for result in search_results.get('organic', []):
                context += f"\nBaşlık: {result.get('title')}\nÖzet: {result.get('snippet')}\n"

            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # TÜM PROMPT TEK BİR TIRNAK İÇİNDE
            prompt = f"""
            SEN BİR YARGITAY ANALİSTİSİN.
            Aşağıdaki verileri kullanarak bir analiz yap:
            OLAY: {olay_ozeti}
            ARAMA VERİLERİ: {context}

            FORMAT:
            - **⚖️ Hukuki Dayanak:** (İlgili Kanun Maddesi)
            - **🔍 Gerçek Emsal:** (Varsa Daire ve Esas/Karar No)
            - **📢 Sonuç:** (Yargıtay'ın genel tavrı)
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Operasyon Hatası: {str(e)}"
