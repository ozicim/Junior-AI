import google.generativeai as genai
import requests
import json

class IctihatEngine:
    @classmethod
    def karar_analiz_et(cls, api_key, karar_metni, soru):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
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
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            # TÜM PROMPT TEK BİR TIRNAK İÇİNDE
            prompt = f"""
            SEN KIDEMLİ BİR HUKUK ANALİSTİ VE YARGITAY UYGULAMALARI UZMANISIN.
            Aşağıda sana internetten (Serper API) gelen ham veriler ve kullanıcının hukuki olayı verilmiştir.
            
            GELEN VERİLER: {context}
            HUKUKİ OLAY: {olay_input}
            
            GÖREVİN:
            1. KESİNLİKLE AMA KESİNLİKLE uydurma Esas/Karar numarası, tarih veya mahkeme ismi VERME. 
            2. Spesifik bir karar metni uydurmaya çalışma.
            3. Görevin sadece "YARGITAY'IN GENEL YÖNELİMİNİ" ve "UYGULAMA TRENDİNİ" analiz etmektir.
            
            ANALİZ FORMATI (Sadece bu başlıkları kullan):
            
            ### 🏛️ YARGITAY YÖNELİM ANALİZİ
            **1. Yerleşik Uygulama Trendi:** Yargıtay bu tip olaylara genel olarak nasıl bakıyor? (Örn: "İşçi lehine yorum ilkesini ön planda tutmaktadır", "Bankanın objektif özen yükümlülüğünü ağırlaştırmaktadır" vb.)
            
            **2. Kritik Eşikler ve Kriterler:** Mahkemenin bir karara varırken aradığı ana şartlar nelerdir? (Hangi durumlarda davayı kabul, hangi durumlarda reddetme eğilimindedir?)
            
            **3. Güncel Yaklaşım Değişiklikleri:** Varsa, son yıllarda bu konudaki içtihatlarda bir esneme veya sertleşme var mı?
            
            **4. Stratejik Hukuki Yorum:** Bu olayda davanın kaderini belirleyecek olan en temel hukuki argüman ne olmalıdır? (İspat yükü, kusur durumu, zaman aşımı vb. açısından yorumla.)
            
            **⚠️ ÖNEMLİ UYARI:** Karar numarası uydurma. Sadece hukuk teorisi ve yüksek mahkemenin "yerleşik uygulaması" üzerinden konuş.
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Operasyon Hatası: {str(e)}"
